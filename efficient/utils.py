import MetaTrader5 as mt5
import pytz
from datetime import datetime, timedelta
from notifications import send_discord_message_async
import asyncio
import logging
from trade_codes import get_trade_return_description

# Global dictionary to store the last message time for each symbol
last_message_time = {}

# Define the interval between messages in seconds
MESSAGE_INTERVAL = 60  # Example: 30 seconds
TRADE_LIMIT = 3  # Maximum of 3 trades per symbol


async def log_error_and_notify(message):
    logging.error(message)
    await send_discord_message_async(message)

async def send_limited_message(symbol, message):
    current_time = datetime.now()
    last_time = last_message_time.get(symbol)
    if last_time is None or (current_time - last_time).total_seconds() > MESSAGE_INTERVAL:
        # Send the message and update the last message time
        logging.info(f"Sending message for {symbol}: {message}")
        await send_discord_message_async(message)
        last_message_time[symbol] = current_time  # Update last sent time
    else:
        # Skip sending the message to respect the rate limit
        logging.info(f"Message for {symbol} rate-limited; not sent.")

async def connect_mt5():
    """Asynchronously initialize and log in to MetaTrader 5."""
    initialized = await asyncio.to_thread(mt5.initialize)
    if not initialized:
        print("Failed to initialize MetaTrader5")
        return False

    login = 213171528  # Replace with actual login
    password = "AHe@Yps3"  # Replace with actual password
    server = "OctaFX-Demo"  # Replace with actual server

    authorized = await asyncio.to_thread(mt5.login, login, password, server)
    if not authorized:
        print(f"Login failed for account {login}")
        return False

    print(f"Successfully logged into account {login} on server {server}")
    return True

async def fetch_current_price(symbol):
    symbol_name = symbol["symbol"]
    # Ensure the symbol is available in Market Watch
    selected = await asyncio.to_thread(mt5.symbol_select, symbol_name, True)
    if not selected:
        await log_error_and_notify(f"Failed to select symbol {symbol_name} for fetching current price.")
        return None

    # Fetch current price
    tick = await asyncio.to_thread(mt5.symbol_info_tick, symbol_name)
    if tick:
        return tick.bid  # or tick.ask depending on your logic
    else:
        await log_error_and_notify(f"Failed to get current price for {symbol_name}")
        return None

async def fetch_start_price(symbol):
    symbol_name = symbol["symbol"]
    now = datetime.now(pytz.timezone('Asia/Kolkata'))

    # Ensure the symbol is available in Market Watch
    selected = await asyncio.to_thread(mt5.symbol_select, symbol_name, True)
    if not selected:
        await log_error_and_notify(f"Failed to select symbol {symbol_name} for fetching start price.")
        return None

    if now.weekday() == 0:  # Monday
        return await fetch_friday_closing_price(symbol)

    start_of_day_utc = now.replace(hour=0, minute=0, second=0).astimezone(pytz.utc)
    rates = await asyncio.to_thread(mt5.copy_rates_from, symbol_name, mt5.TIMEFRAME_M5, start_of_day_utc, 1)

    if rates:
        start_price = rates[0]["close"]
        print(f"Fetched start price for {symbol_name}: {start_price}")
        return start_price

    await log_error_and_notify(f"Failed to get start price for {symbol_name}")
    return None

async def fetch_price(symbol, price_type):
    """Fetch price based on type, reusing code for start and current prices."""
    symbol_name = symbol["symbol"]

    # Ensure the symbol is selected in Market Watch
    selected = await asyncio.to_thread(mt5.symbol_select, symbol_name, True)
    if not selected:
        await log_error_and_notify(f"Failed to select symbol {symbol_name} for fetching {price_type} price.")
        return None

    if price_type == "current":
        tick = await asyncio.to_thread(mt5.symbol_info_tick, symbol_name)
        if tick:
            return tick.bid  # or tick.ask depending on requirements

    elif price_type == "start":
        now = datetime.now(pytz.timezone('Asia/Kolkata'))
        if now.weekday() == 0:  # Monday
            return await fetch_friday_closing_price(symbol)

        start_of_day_utc = now.replace(hour=0, minute=0, second=0).astimezone(pytz.utc)
        rates = await asyncio.to_thread(mt5.copy_rates_from, symbol_name, mt5.TIMEFRAME_M5, start_of_day_utc, 1)
        if rates:
            return rates[0]["close"]

    await log_error_and_notify(f"Failed to get {price_type} price for {symbol_name}")
    return None

async def fetch_friday_closing_price(symbol):
    """Asynchronously fetch the last Friday's closing price for a symbol."""
    today = datetime.now(pytz.timezone('Asia/Kolkata'))
    symbol_name = symbol["symbol"]
    days_ago = (today.weekday() + 3) % 7 + 2
    last_friday = today - timedelta(days=days_ago)
    last_friday = last_friday.replace(hour=23, minute=59, second=59)
    utc_from = last_friday.astimezone(pytz.utc)

    rates = await asyncio.to_thread(mt5.copy_rates_from, symbol["symbol"], mt5.TIMEFRAME_M5, utc_from, 1)
    if rates is not None and len(rates) > 0:
        closing_price = rates[0]['close']
        print(f"Fetched last Friday's closing price for {symbol_name}: {closing_price}")
        return closing_price

    print(f"Failed to get last Friday's closing price for {symbol_name}")
    return None

async def place_trade_notify(symbol, action, lot_size):
    """Asynchronously place a trade and notify via Discord."""
    open_positions = await get_open_positions({"symbol": symbol})
    if open_positions["no_of_positions"] >= TRADE_LIMIT:
        await send_limited_message(symbol, f"Trade limit reached for {symbol}. No further trades will be placed.")
        return  # Skip trade placement if limit is reached
    if not await connect_mt5():
        return
    selected = await asyncio.to_thread(mt5.symbol_select, symbol, True)
    if not selected:
        print(f"Failed to select symbol {symbol}")
        return

    price_info = await asyncio.to_thread(mt5.symbol_info_tick, symbol)
    if price_info is None:
        print(f"Failed to get tick information for {symbol}")
        return

    price = price_info.ask if action == 'buy' else price_info.bid
    lot = lot_size if lot_size is not None else 1.0
    deviation = 50

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": mt5.ORDER_TYPE_BUY if action == 'buy' else mt5.ORDER_TYPE_SELL,
        "price": price,
        "deviation": deviation,
        "magic": 234000,
        "comment": "python script open",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }

    result = await asyncio.to_thread(mt5.order_send, request)

    if result is None:
        message = f"Order send error: {mt5.last_error()}"
        print(message)
        await send_discord_message_async(message)
    else:
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            message = f"Trade request failed for {symbol}, retcode={result.retcode}"
        else:
            now = datetime.now()
            message = f"Trade executed successfully at {now}, order={result}"

        print(message)
        await send_limited_message(symbol,message)

async def hedge_place_trade(symbol, action, lot_size):
    """Asynchronously place a hedge trade without being restricted by trade limits and notify via Discord."""
    if not await connect_mt5():
        return
    selected = await asyncio.to_thread(mt5.symbol_select, symbol, True)
    if not selected:
        print(f"Failed to select symbol {symbol}")
        return

    price_info = await asyncio.to_thread(mt5.symbol_info_tick, symbol)
    if price_info is None:
        print(f"Failed to get tick information for {symbol}")
        return

    price = price_info.ask if action == 'buy' else price_info.bid
    lot = lot_size if lot_size is not None else 1.0
    deviation = 50

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": mt5.ORDER_TYPE_BUY if action == 'buy' else mt5.ORDER_TYPE_SELL,
        "price": price,
        "deviation": deviation,
        "magic": 234000,
        "comment": "hedge trade by script",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }

    result = await asyncio.to_thread(mt5.order_send, request)

    if result is None:
        message = f"Order send error: {mt5.last_error()}"
        print(message)
        await send_discord_message_async(message)
    else:
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            message = f"Hedge trade request failed for {symbol}, retcode={result.retcode}"
        else:
            now = datetime.now()
            message = f"Hedge trade executed successfully at {now}, order={result}"

        print(message)
        await send_limited_message(symbol, message)

async def close_trades_by_symbol(symbol):
    """Asynchronously close all open trades for a symbol."""
    if not await connect_mt5():
        return

    open_positions = await asyncio.to_thread(mt5.positions_get, symbol=symbol)

    if open_positions is None or len(open_positions) == 0:
        print(f"No open positions for {symbol}.")
        return

    for position in open_positions:
        ticket = position.ticket
        lot = position.volume
        trade_type = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        symbol_info = await asyncio.to_thread(mt5.symbol_info, symbol)

        if symbol_info is None:
            print(f"Symbol {symbol} not found.")
            continue

        price = symbol_info.bid if trade_type == mt5.ORDER_TYPE_SELL else symbol_info.ask

        close_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": trade_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": 123456,
            "comment": "Closing trade by script",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }

        result = await asyncio.to_thread(mt5.order_send, close_request)

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            message = f"Failed to close trade {ticket} for {symbol}, error code: {result.retcode}"
        else:
            message = f"Successfully closed trade {ticket} for {symbol}."

        print(message)
        await send_limited_message(message)

async def format_message(message_type, data):
    """Asynchronously format messages for notifications and hourly updates."""
    direction_symbols = {"Upper": "↑", "Down": "↓", "Neutral": "-"}
    direction_symbol = direction_symbols.get(data["direction"], "-")

    if message_type == "pip_difference":
        formatted_message = f"""
        **{data["symbol"]} {direction_symbol}**

        **Start Price:** **{data["start_price"]}**
        **Current Price:** **{data["current_price"]}**
        **Pip Difference:** **{data["pip_difference"]}**
        **Direction:** {direction_symbol} {data["direction"]}
        """
        return formatted_message.strip()
    elif message_type == "hourly_update":
        formatted_message = f"""
        --------------------------------------------------Hourly Update--------------------------------------------------

        **Symbol:** {data["symbol"]}
        **Start Price:** **{data["start_price"]}**
        **Current Price:** **{data["current_price"]}**
        **Pip Difference:** **{data["pip_difference"]}**
        **Direction:** {direction_symbol} {data["direction"]}
        **Pips to Positive Threshold:** {data["pips_to_positive_threshold"]}
        **Pips to Negative Threshold:** {data["pips_to_negative_threshold"]}
        """
        return formatted_message.strip()
    else:
        return str(data)

async def fetch_and_print_price(symbol_data):
    """Asynchronously fetch and print current price."""
    symbol_name = symbol_data["symbol"]
    current_price = await fetch_current_price(symbol_name)
    start_price = symbol_data["start_price"]

    if current_price is not None and start_price is not None:
        pip_diff = round((current_price - start_price) / 0.0001, 3)
        print(f"{symbol_name}: Start {start_price}, Current {current_price}, Pips: {pip_diff}")
        message = f"{symbol_name}: Start {start_price}, Current {current_price}, Pips: {pip_diff}"
        await send_discord_message_async(message)

async def get_open_positions(symbol):
    """Fetch open positions for a symbol and return position details consistently."""
    open_positions = {"positions_exist": False, "no_of_positions": 0}  # Set default values
    symbol_name = symbol["symbol"]

    # Attempt to get open positions for the symbol
    positions = await asyncio.to_thread(mt5.positions_get, symbol=symbol_name)

    if positions is None:
        # Notify if there are no positions or an error occurred
        message = f"No positions exist for {symbol_name} at {datetime.now()}"
        await send_limited_message(symbol_name, message)
    elif len(positions) > 0:
        open_positions["positions_exist"] = True
        open_positions["no_of_positions"] = len(positions)

    return open_positions

async def fetch_pip_difference(current_price, start_price):
    return current_price-start_price

async def check_opposite_direction_and_close_trades_and_hedge(symbol, threshold, direction):
    symbol_name = symbol["symbol"]
    if threshold <= 0.5:
        position_data = await get_open_positions(symbol)

        if position_data["positions_exist"] and position_data["no_of_positions"] > 1:
            await close_trades_by_symbol(symbol_name)

        for _ in range(3):
            await hedge_place_trade(symbol_name, direction, 1)

async def check_threshold_and_place_trade(symbol,action,threshold):
    if threshold == 1:
        result = await place_trade_notify(symbol["symbol"], action, symbol["lot_size"])
        return result

async def check_threshold_and_close_trade(symbol, thresholds_reached):
    # Ensure the function can handle any threshold greater than or equal to 2
    if thresholds_reached >= 2:
        symbol_name = symbol["symbol"]
        message = f"{symbol_name} has reached {thresholds_reached} thresholds, attempting to close trades."
        await send_limited_message(symbol_name, message)

        position_data = await get_open_positions(symbol)

        if position_data["positions_exist"]:
            # Cast thresholds_reached to an integer before using in range
            for _ in range(int(thresholds_reached)):  # Corrected here to convert to int
                result = await close_trades_by_symbol(symbol_name)

                # Check if result is None before accessing retcode
                if result is None:
                    error_msg = f"Failed to close position for {symbol_name}; result is None."
                    await send_limited_message(symbol_name, error_msg)
                    break  # Stop trying if closing fails

                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    error_msg = f"Failed to close position for {symbol_name}, retcode={result.retcode}"
                    await send_limited_message(symbol_name, error_msg)
                    break  # Stop trying if closing fails

                success_msg = f"Successfully closed a position for {symbol_name}."
                await send_limited_message(symbol_name, success_msg)
            return result
        else:
            no_position_msg = f"No open positions to close for {symbol_name}."
            await send_limited_message(symbol_name,no_position_msg)

async def check_thresholds(symbol, pip_difference):
    no_of_thresholds_reached = 0
    data = {"symbol": symbol["symbol"], "direction": "neutral", "thresholds": no_of_thresholds_reached}
    format_threshold = pip_difference / symbol["pip_size"]
    symbol_name = symbol["symbol"]


    positive_difference = symbol["positive_pip_difference"]
    negative_difference = symbol["negative_pip_difference"]


    if format_threshold >= positive_difference:
        no_of_thresholds_reached = format_threshold // positive_difference
        data["direction"] = "up"
        data["thresholds"] = no_of_thresholds_reached
        await check_threshold_and_place_trade(symbol, "buy", no_of_thresholds_reached)
        print(f"Up direction, thresholds reached: {symbol_name} {no_of_thresholds_reached}")
        await check_threshold_and_close_trade(symbol, no_of_thresholds_reached)
        await check_opposite_direction_and_close_trades_and_hedge(symbol, no_of_thresholds_reached, "sell")




    elif format_threshold <= negative_difference:
        no_of_thresholds_reached = abs(format_threshold) // abs(negative_difference)
        data["direction"] = "down"
        data["thresholds"] = no_of_thresholds_reached
        await check_threshold_and_place_trade(symbol, "sell", no_of_thresholds_reached)
        print(f"Down direction, thresholds reached:{symbol_name} {no_of_thresholds_reached}")
        await check_threshold_and_close_trade(symbol, no_of_thresholds_reached)
        await check_opposite_direction_and_close_trades_and_hedge(symbol, no_of_thresholds_reached, "buy")




    else:
        data["direction"] = "neutral"
        data["thresholds"] = no_of_thresholds_reached
        print(f"Neutral direction, Noo thresholds reached.{symbol_name}")
        await check_threshold_and_close_trade(symbol, no_of_thresholds_reached)

    return data

async def check_thresholds_and_place_trades(symbol, start_price, current_price):
    difference = await fetch_pip_difference(current_price ,start_price)
    data= await check_thresholds(symbol, difference)
    return data







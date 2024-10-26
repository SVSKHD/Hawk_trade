import MetaTrader5 as mt5
import pytz
from datetime import datetime, timedelta
from notifications import send_discord_message_async
import asyncio


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
    """Asynchronously fetch the current price for a symbol."""
    tick = await asyncio.to_thread(mt5.symbol_info_tick, symbol_name)
    if tick:
        return tick.bid  # or tick.ask depending on your logic
    else:
        print(f"Failed to get current price for {symbol}")
        return None

async def fetch_start_price(symbol):
    symbol_name = symbol["symbol"]
    """Asynchronously fetch the start price of the day for a symbol."""
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)

    if now.weekday() == 0:  # Monday
        start_price = await fetch_friday_closing_price(symbol)
    else:
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        utc_from = start_of_day.astimezone(pytz.utc)

        rates = await asyncio.to_thread(mt5.copy_rates_from, symbol_name, mt5.TIMEFRAME_M5, utc_from, 1)
        if rates is not None and len(rates) > 0:
            start_price = rates[0]['close']
        else:
            print(f"Failed to get start price for {symbol}")
            return None

    if start_price:
        print(f"Fetched start price for {symbol}: {start_price}")
    return start_price

async def fetch_friday_closing_price(symbol):
    """Asynchronously fetch the last Friday's closing price for a symbol."""
    today = datetime.now(pytz.timezone('Asia/Kolkata'))
    days_ago = (today.weekday() + 3) % 7 + 2
    last_friday = today - timedelta(days=days_ago)
    last_friday = last_friday.replace(hour=23, minute=59, second=59)
    utc_from = last_friday.astimezone(pytz.utc)

    rates = await asyncio.to_thread(mt5.copy_rates_from, symbol, mt5.TIMEFRAME_M5, utc_from, 1)
    if rates is not None and len(rates) > 0:
        closing_price = rates[0]['close']
        print(f"Fetched last Friday's closing price for {symbol}: {closing_price}")
        return closing_price

    print(f"Failed to get last Friday's closing price for {symbol}")
    return None

async def place_trade_notify(symbol, action, lot_size):
    """Asynchronously place a trade and notify via Discord."""
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
        await send_discord_message_async(message)

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
        await send_discord_message_async(message)

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
    open_positions = {"position_exist":False, "no_of_positions":0}
    symbol_name = symbol["symbol"]
    positions = mt5.positions_get(symbol["symbol"])
    if positions is None:
        message = f"no postions exist in {symbol_name} at  {datetime.now()}"
        await send_discord_message_async(message)
        return open_positions
    if len(positions)>0:
        open_positions["positions_exist"]=True
        open_positions["no_of_positions"] = len(positions)
        return open_positions


async def fetch_pip_difference(current_price, start_price):
    return current_price-start_price

async def check_threshold_and_place_trade(symbol,action,threshold):
    if threshold == 1:
        result = await place_trade_notify(symbol["symbol"], action, symbol["lot_size"])
        return result
    elif threshold == 2:
        position = await get_open_positions(symbol)
        if position["position_exist"]:
            result = await close_trades_by_symbol(symbol["symbol"])
            return result


async def check_threshold_and_close_trade(symbol, threshold):
    if threshold==2:
        await close_trades_by_symbol(symbol["symbol"])

async def check_thresholds(symbol, pip_difference):
    no_of_thresholds_reached = 0
    data = {"symbol": symbol["symbol"], "direction": "neutral", "thresholds": no_of_thresholds_reached}
    # Format pip difference based on pip size
    format_threshold = pip_difference / symbol["pip_size"]

    # Extract positive and negative differences from the symbol configuration
    positive_difference = symbol["positive_pip_difference"]
    negative_difference = symbol["negative_pip_difference"]


    # Check for positive direction
    if format_threshold >= positive_difference:
        no_of_thresholds_reached = format_threshold // positive_difference
        data["direction"] = "up"
        data["thresholds"] = no_of_thresholds_reached
        print(f"Up direction, thresholds reached: {no_of_thresholds_reached}")


    # Check for negative direction
    elif format_threshold <= negative_difference:
        no_of_thresholds_reached = abs(format_threshold) // abs(negative_difference)
        data["direction"] = "down"
        data["thresholds"] = no_of_thresholds_reached
        print(f"Down direction, thresholds reached: {no_of_thresholds_reached}")

    # If the threshold is not reached, set to neutral
    else:
        data["direction"] = "neutral"
        data["thresholds"] = no_of_thresholds_reached
        print("Neutral direction, no thresholds reached.")

    return data


async def check_thresholds_and_place_trades(symbol, start_price, current_price):
    difference = await fetch_pip_difference(current_price ,start_price)
    data= await check_thresholds(symbol, difference)
    print("data", data)
    return data








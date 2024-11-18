import MetaTrader5 as mt5
import asyncio
from datetime import datetime, timedelta
import pytz
from config import symbols_config  # Import symbols_config from config.py
import logging
from notifications import send_discord_message_async

# Dictionaries to store prices
start_prices = {}
current_prices = {}

MESSAGE_INTERVAL = 60  # Interval for limiting message sending, in seconds
last_message_time = {}  # Store last message sent time for each symbol

TRADE_LIMIT = 3  # Maximum of 3 trades per symbol


async def send_limited_message(symbol, message):
    current_time = datetime.now()
    last_time = last_message_time.get(symbol)
    if last_time is None or (current_time - last_time).total_seconds() > MESSAGE_INTERVAL:
        logging.info(f"Sending message for {symbol}: {message}")
        await send_discord_message_async(message)
        last_message_time[symbol] = current_time
    else:
        logging.info(f"Message for {symbol} rate-limited; not sent.")


async def log_error_and_notify(message):
    logging.error(message)
    await send_limited_message("general", message)


async def connect_mt5():
    """Asynchronously initialize and log in to MetaTrader 5."""
    initialized = await asyncio.to_thread(mt5.initialize)
    if not initialized:
        await log_error_and_notify("Failed to initialize MetaTrader5")
        return False

    login = 213171528
    password = "AHe@Yps3"
    server = "OctaFX-Demo"

    authorized = await asyncio.to_thread(mt5.login, login, password, server)
    if not authorized:
        await log_error_and_notify(f"Login failed for account {login}")
        return False

    logging.info(f"Successfully logged into account {login} on server {server}")
    return True


# trade_management
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
        await send_limited_message(symbol, message)


async def fetch_current_price(symbol_config):
    """Fetch the current price of a given symbol."""
    symbol_name = symbol_config["symbol"]
    selected = await asyncio.to_thread(mt5.symbol_select, symbol_name, True)
    if not selected:
        await log_error_and_notify(f"Failed to select symbol {symbol_name} for fetching current price.")
        return None

    tick = await asyncio.to_thread(mt5.symbol_info_tick, symbol_name)
    return tick.bid if tick else None


async def fetch_start_price(symbol):
    """Fetch the start price of the day or last Friday closing price for a given symbol."""
    symbol_name = symbol["symbol"]
    now = datetime.now(pytz.timezone('Asia/Kolkata'))
    selected = await asyncio.to_thread(mt5.symbol_select, symbol_name, True)

    if not selected:
        await log_error_and_notify(f"Failed to select symbol {symbol_name} for fetching start price.")
        return None

    if now.weekday() == 0:
        return await fetch_friday_closing_price(symbol)

    start_of_day_utc = now.replace(hour=0, minute=0, second=0).astimezone(pytz.utc)
    rates = await asyncio.to_thread(mt5.copy_rates_from, symbol_name, mt5.TIMEFRAME_M5, start_of_day_utc, 1)

    if rates:
        start_price = rates[0]["close"]
        logging.info(f"Fetched start price for {symbol_name}: {start_price}")
        return start_price

    await log_error_and_notify(f"Failed to get start price for {symbol_name}")
    return None


async def fetch_friday_closing_price(symbol):
    """Asynchronously fetch the last Friday's closing price for a symbol."""
    today = datetime.now(pytz.timezone('Asia/Kolkata'))
    symbol_name = symbol["symbol"]
    days_ago = (today.weekday() + 3) % 7 + 2
    last_friday = today - timedelta(days=days_ago)
    last_friday = last_friday.replace(hour=23, minute=59, second=59)
    utc_from = last_friday.astimezone(pytz.utc)

    rates = await asyncio.to_thread(mt5.copy_rates_from, symbol_name, mt5.TIMEFRAME_M5, utc_from, 1)
    if rates and len(rates) > 0:
        closing_price = rates[0]['close']
        logging.info(f"Fetched last Friday's closing price for {symbol_name}: {closing_price}")
        return closing_price

    await log_error_and_notify(f"Failed to get last Friday's closing price for {symbol_name}")
    return None


async def get_open_positions(symbol):
    """Fetch open positions for a symbol and return position details consistently."""
    symbol_name = symbol["symbol"]
    positions = await asyncio.to_thread(mt5.positions_get, symbol=symbol_name)

    open_positions = {
        "positions_exist": len(positions) > 0,
        "no_of_positions": len(positions) if positions else 0
    }

    if not positions:
        await send_limited_message(symbol_name, f"No positions exist for {symbol_name} at {datetime.now()}")

    return open_positions


async def fetch_pip_difference(current_price, start_price):
    """Calculate the pip difference between current and start price."""
    return current_price - start_price


async def check_thresholds_and_place_trades(symbol, start_price, current_price):
    """Check the pip difference and place or close trades accordingly."""
    difference = await fetch_pip_difference(current_price, start_price)
    format_threshold = difference / symbol["pip_size"]
    symbol_name = symbol["symbol"]

    positive_difference = symbol["positive_pip_difference"]
    negative_difference = symbol["negative_pip_difference"]

    if format_threshold >= positive_difference:
        thresholds_reached = format_threshold // positive_difference
        await handle_threshold_reached(symbol, thresholds_reached, "buy", "sell")
    elif format_threshold <= negative_difference:
        thresholds_reached = abs(format_threshold) // abs(negative_difference)
        await handle_threshold_reached(symbol, thresholds_reached, "sell", "buy")
    else:
        logging.info(f"Neutral direction, no thresholds reached for {symbol_name}")


async def handle_threshold_reached(symbol, thresholds_reached, action, opposite_action):
    """Handle trades when thresholds are reached."""
    symbol_name = symbol["symbol"]

    if thresholds_reached >= 1:
        await check_threshold_and_place_trade(symbol, action, thresholds_reached)
        await check_threshold_and_close_trade(symbol, thresholds_reached)
        await check_opposite_direction_and_close_trades_and_hedge(symbol, thresholds_reached, opposite_action)


async def check_threshold_and_place_trade(symbol, action, threshold):
    """Place a trade if the threshold is met."""
    if threshold >= 1:
        await place_trade_notify(symbol["symbol"], action, symbol["lot_size"])


async def check_threshold_and_close_trade(symbol, thresholds_reached):
    """Close trades if the thresholds are reached."""
    if thresholds_reached >= 2:
        symbol_name = symbol["symbol"]
        await send_limited_message(symbol_name, f"{symbol_name} has reached {thresholds_reached} thresholds, attempting to close trades.")

        position_data = await get_open_positions(symbol)
        if position_data["positions_exist"]:
            for _ in range(int(thresholds_reached)):
                result = await close_trades_by_symbol(symbol_name)
                if not result or result.retcode != mt5.TRADE_RETCODE_DONE:
                    await send_limited_message(symbol_name, f"Failed to close position for {symbol_name}, retcode={getattr(result, 'retcode', 'None')}")
                    break
                await send_limited_message(symbol_name, f"Successfully closed a position for {symbol_name}.")


async def check_opposite_direction_and_close_trades_and_hedge(symbol, threshold, direction):
    """Hedge trades and close opposite trades if certain thresholds are reached."""
    if threshold <= 0.5:
        position_data = await get_open_positions(symbol)
        if position_data["positions_exist"] and position_data["no_of_positions"] > 1:
            await close_trades_by_symbol(symbol["symbol"])

        for _ in range(3):
            await hedge_place_trade(symbol["symbol"], direction, 1)


async def runBot():
    # Step 1: Connect to MetaTrader5
    while not await connect_mt5():
        await asyncio.sleep(1)

    # Step 2: Fetch start prices once
    start_price_tasks = [fetch_start_price(symbol_config) for symbol_config in symbols_config]
    start_prices_results = await asyncio.gather(*start_price_tasks)

    # Store start prices
    for symbol_config, start_price in zip(symbols_config, start_prices_results):
        if start_price is not None:
            start_prices[symbol_config["symbol"]] = start_price

    # Step 3: Fetch current prices and check thresholds every second
    while True:
        current_price_tasks = [fetch_current_price(symbol_config) for symbol_config in symbols_config]
        current_prices_results = await asyncio.gather(*current_price_tasks)

        for symbol_config, current_price in zip(symbols_config, current_prices_results):
            if current_price is not None:
                current_prices[symbol_config["symbol"]] = current_price
                await check_thresholds_and_place_trades(symbol_config, start_prices[symbol_config["symbol"]], current_price)

        await asyncio.sleep(1)

# Run the bot
if __name__ == "__main__":
    asyncio.run(runBot())

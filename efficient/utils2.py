import MetaTrader5 as mt5
import pytz
from datetime import datetime, timedelta
from notifications import send_limited_message, send_discord_message_async
import asyncio
import logging
from trade_codes import get_trade_return_description

# Global dictionary to store the last message time for each symbol
TRADE_LIMIT = 3  # Maximum of 3 trades per symbol

async def log_error_and_notify(message):
    logging.error(message)
    await send_discord_message_async(message)



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

async def fetch_friday_closing_price(symbol):
    """Asynchronously fetch the last Friday's closing price for a symbol."""
    today = datetime.now(pytz.timezone('Asia/Kolkata'))
    symbol_name = symbol["symbol"]
    days_ago = (today.weekday() + 3) % 7 + 2
    last_friday = today - timedelta(days=days_ago)
    last_friday = last_friday.replace(hour=23, minute=59, second=59)
    utc_from = last_friday.astimezone(pytz.utc)

    rates = await asyncio.to_thread(mt5.copy_rates_from, symbol_name, mt5.TIMEFRAME_M5, utc_from, 1)
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
        await send_limited_message(symbol, message)

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

async def get_open_positions(symbol):
    """Fetch open positions for a symbol and return position details consistently."""
    open_positions = {"positions_exist": False, "no_of_positions": 0}  # Set default values
    symbol_name = symbol["symbol"]

    # Attempt to get open positions for the symbol
    positions = await asyncio.to_thread(mt5.positions_get, symbol=symbol_name)

    if positions is None or len(positions) == 0:
        # Notify if there are no positions or an error occurred
        message = f"No positions exist for {symbol_name} at {datetime.now()}"
        await send_limited_message(symbol_name, message)
    else:
        open_positions["positions_exist"] = True
        open_positions["no_of_positions"] = len(positions)

    return open_positions

def calculate_thresholds_crossed(pip_difference_in_pips, positive_threshold, negative_threshold):
    """Calculate the number of thresholds crossed and the direction."""
    if pip_difference_in_pips >= positive_threshold:
        thresholds_crossed = int(pip_difference_in_pips / positive_threshold)
        direction = 'up'
    elif pip_difference_in_pips <= negative_threshold:
        thresholds_crossed = int(abs(pip_difference_in_pips) / abs(negative_threshold))
        direction = 'down'
    else:
        thresholds_crossed = 0
        direction = 'neutral'
    return thresholds_crossed, direction

async def handle_thresholds(symbol, thresholds_crossed, direction):
    """Handle actions based on the number of thresholds crossed."""
    symbol_name = symbol["symbol"]
    lot_size = symbol.get("lot_size", 1.0)
    max_trade_limit = symbol.get("max_trade_limit", TRADE_LIMIT)

    if thresholds_crossed == 0:
        # Neutral, no action needed
        print(f"No thresholds crossed for {symbol_name}.")
        return
    elif thresholds_crossed == 1:
        # First threshold crossed
        # Check if we can place a trade
        open_positions = await get_open_positions({"symbol": symbol_name})
        if open_positions["no_of_positions"] < max_trade_limit:
            # Place trade in the direction
            await place_trade_notify(symbol_name, 'buy' if direction == 'up' else 'sell', lot_size)
        else:
            print(f"Trade limit reached for {symbol_name}. Cannot place new trade.")
    elif thresholds_crossed >= 2:
        # Multiple thresholds crossed
        # Close existing positions
        await close_trades_by_symbol(symbol_name)
        # Place hedge trades if desired
        opposite_direction = 'sell' if direction == 'up' else 'buy'
        num_hedge_trades = thresholds_crossed - 1
        for _ in range(num_hedge_trades):
            await hedge_place_trade(symbol_name, opposite_direction, lot_size)
    else:
        # Should not reach here
        print(f"Unexpected thresholds crossed value: {thresholds_crossed} for {symbol_name}")

async def check_thresholds_and_place_trades(symbol, start_price, current_price):
    """Check thresholds and place trades accordingly."""
    pip_difference = current_price - start_price
    pip_difference_in_pips = pip_difference / symbol["pip_size"]
    positive_threshold = symbol["positive_pip_difference"]
    negative_threshold = symbol["negative_pip_difference"]
    thresholds_crossed, direction = calculate_thresholds_crossed(
        pip_difference_in_pips, positive_threshold, negative_threshold)
    data = {"symbol": symbol["symbol"], "direction": direction, "thresholds": thresholds_crossed}

    print(f"{symbol['symbol']} | Pip Difference: {pip_difference_in_pips} | Direction: {direction} | Thresholds crossed: {thresholds_crossed}")

    await handle_thresholds(symbol, thresholds_crossed, direction)

    return data

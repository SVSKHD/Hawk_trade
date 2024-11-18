import MetaTrader5 as mt5
import logging
import asyncio
from datetime import datetime, timedelta
import pytz

from notifications import send_discord_message_async  # Ensure this function is asynchronous

async def log_error_and_notify(message):
    logging.error(message)
    await send_discord_message_async(message)

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

async def fetch_friday_closing_price(symbol):
    """Asynchronously fetch the last Friday's closing price for a symbol."""
    timezone = pytz.timezone('Asia/Kolkata')
    today = datetime.now(timezone)
    symbol_name = symbol["symbol"]
    days_since_friday = (today.weekday() - 4) % 7
    last_friday = today - timedelta(days=days_since_friday)
    last_friday = last_friday.replace(hour=23, minute=59, second=59, microsecond=0)
    utc_from = last_friday.astimezone(pytz.utc)

    rates = await asyncio.to_thread(mt5.copy_rates_from, symbol_name, mt5.TIMEFRAME_M5, utc_from, 1)
    if rates is not None and len(rates) > 0:
        closing_price = rates[0]['close']
        print(f"Fetched last Friday's closing price for {symbol_name}: {closing_price}")
        return closing_price

    await log_error_and_notify(f"Failed to get last Friday's closing price for {symbol_name}")
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
        timezone = pytz.timezone('Asia/Kolkata')
        now = datetime.now(timezone)
        if now.weekday() == 0:  # Monday
            return await fetch_friday_closing_price(symbol)

        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_day_utc = start_of_day.astimezone(pytz.utc)
        rates = await asyncio.to_thread(mt5.copy_rates_from, symbol_name, mt5.TIMEFRAME_M5, start_of_day_utc, 1)
        if rates is not None and len(rates) > 0:
            return rates[0]["close"]

    await log_error_and_notify(f"Failed to get {price_type} price for {symbol_name}")
    return None

async def fetch_start_and_current_price(symbol):
    symbol_name = symbol["symbol"]
    print(f"Fetching prices for {symbol_name}")

    # Fetch start price and current price concurrently
    start_price_task = asyncio.create_task(fetch_price(symbol, "start"))
    current_price_task = asyncio.create_task(fetch_price(symbol, "current"))

    # Await the results
    start_price = await start_price_task
    current_price = await current_price_task

    # Check if both prices were fetched successfully
    if start_price is None or current_price is None:
        await log_error_and_notify(f"Failed to fetch prices for {symbol_name}")
        return None

    print(f"Fetched prices for {symbol_name}: Start Price = {start_price}, Current Price = {current_price}")
    return {"start_price": start_price, "current_price": current_price}

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
        **ThresHolds:**{data["threshold"]},
        **Trade_Open:**{data["trade_open"]},
        **Pips to Positive Threshold:** {data["pips_to_positive_threshold"]}
        **Pips to Negative Threshold:** {data["pips_to_negative_threshold"]}
        """
        return formatted_message.strip()
    else:
        return str(data)

async def get_open_positions_scheduler(symbol):
    symbol_name=symbol["symbol"]
    open_positions = {"positions_exist": False, "no_of_positions": 0}  # Set default values

    # Attempt to get open positions for the symbol
    positions = await asyncio.to_thread(mt5.positions_get, symbol=symbol_name)

    if positions is None:
        # Notify if there are no positions or an error occurred
        message = f"No positions exist for {symbol} at {datetime.now()}"
    elif len(positions) > 0:
        open_positions["positions_exist"] = True
        open_positions["no_of_positions"] = len(positions)

    return open_positions
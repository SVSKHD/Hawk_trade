import MetaTrader5 as mt5
import time
from datetime import datetime, timedelta, timezone
import os
import json

current_dir = os.path.dirname(os.path.abspath(__file__))

# Create the full path to details.json
details_path = os.path.join(current_dir, 'details.json')

# Load details from details.json
with open(details_path) as f:
    config = json.load(f)

symbols = config['symbols']


def initialize_mt5():
    if not mt5.initialize():
        print("Failed to initialize MetaTrader 5")
        quit()


def is_market_open(symbol):
    # Get the symbol information
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        raise ValueError(f"Failed to get market info for {symbol}. Ensure the symbol is correct.")

    # Check if the market is open based on trade_mode (4 = full trading allowed)
    if symbol_info.trade_mode == 4:
        return True
    else:
        print(f"Market is closed or trading is restricted for {symbol}. Trade mode: {symbol_info.trade_mode}")
        return False


def get_tick_values(symbol):
    # Get the tick information for the symbol
    tick_info = mt5.symbol_info_tick(symbol)
    if tick_info is None:
        raise ValueError(f"Failed to get tick info for {symbol}. Ensure the symbol is correct and active.")

    # Print and return the relevant tick data
    tick_data = {
        "symbol": symbol,
        "bid": tick_info.bid,
        "ask": tick_info.ask,
        "last": tick_info.last,
        "time": tick_info.time
    }

    print(f"Tick data for {symbol}: {tick_data}")
    return tick_data


def get_previous_friday_close(symbol):
    # Get the current date and time in UTC
    today = datetime.now(timezone.utc)

    # Correctly calculate the previous Friday in UTC
    if today.weekday() == 5:  # If today is Saturday
        last_friday = today - timedelta(days=3)
    elif today.weekday() == 6:  # If today is Sunday
        last_friday = today - timedelta(days=3)
    else:  # If it's Monday to Friday, subtract days to get to last Friday
        last_friday = today - timedelta(days=today.weekday() + 3)

    # Ensure the time is set to Friday 23:00:00 UTC for the closing tick
    friday_close_time = datetime(last_friday.year, last_friday.month, last_friday.day, 23, 59, 0, tzinfo=timezone.utc)
    one_minute_after_friday_close = friday_close_time + timedelta(minutes=1)

    # Fetch the tick data around last Friday's closing time
    ticks = mt5.copy_ticks_range(symbol, friday_close_time, one_minute_after_friday_close, mt5.COPY_TICKS_ALL)

    if ticks is None or len(ticks) == 0:
        print(f"No ticks found for {symbol} at last Friday's close.")
        return None

    # Get the last available tick on Friday before the market closed
    tick = ticks[-1]
    return tick


def get_1am_server_time_price(symbol, price_fetched):
    now = datetime.now(timezone.utc)

    # Check if today is Monday and if the price has already been fetched
    if now.weekday() == 0 and not price_fetched:
        price_fetched = True
        return get_previous_friday_close(symbol), price_fetched

    # Calculate 1 AM in server time and convert it to UTC
    server_offset_hours = 3  # Assuming the server is in EET (UTC+3 during DST)
    server_time_offset = timedelta(hours=server_offset_hours)
    today_1am_server_time = datetime(now.year, now.month, now.day, 1, 0, tzinfo=timezone.utc) - server_time_offset

    # Extend the time range by 5 minutes for fetching tick data
    five_minutes_after_1am = today_1am_server_time + timedelta(minutes=5)

    # Fetch tick data for 1 AM server time
    ticks = mt5.copy_ticks_range(symbol, today_1am_server_time, five_minutes_after_1am, mt5.COPY_TICKS_ALL)

    if ticks is None or len(ticks) == 0:
        print(f"No ticks found for {symbol} at 1 AM server time.")
        return None, price_fetched

    # Get the first available tick after 1 AM
    tick = ticks[0]
    tick_data = {
        "symbol": symbol,
        "bid": tick.bid,
        "ask": tick.ask,
        "last": tick.last
    }
    print(f"Tick data at 1 AM server time for {symbol}: {tick_data}")
    return tick_data, price_fetched


def set_start_prices(symbol, price_fetched):
    tick_data, price_fetched = get_1am_server_time_price(symbol, price_fetched)
    if tick_data:
        print(f"Start price for {symbol} set at 1 AM: {tick_data}")
    return price_fetched


def main():
    initialize_mt5()
    price_fetched = False  # Track if Monday's price has been fetched

    # Loop through symbols and check for market and tick data
    for sym in symbols:
        symbol = sym['symbol']
        take_profit = sym['close_trade_at']
        side_ways_close = sym['close_trade_at_opposite_direction']
        print(f"Processing symbol: {symbol}, {take_profit}, {side_ways_close}")

        # Check if the market is open for the symbol
        if is_market_open(symbol):
            while True:
                # Fetch tick values for the symbol
                get_tick_values(symbol)
                set_start_prices(symbol,price_fetched)
                # Add a condition to break the loop after fetching tick data
                # For now, we break after fetching once for this example
                break

                # Wait for 1 second before checking again
                time.sleep(1)

if __name__ == "__main__":
    main()


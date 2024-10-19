import time
from notifications import send_discord_message
from datetime import datetime, timedelta
import pytz
import MetaTrader5 as mt5  # Ensure MetaTrader5 is imported
from db import save_or_update_threshold_in_mongo
from pip_difference import pip_difference
from poc3 import start_prices

price_array_update = []

start_time = time.time()
last_hourly_check = time.time()
counter = 1

symbols_config = [
    {
        "symbol": "BTCUSD",
        "pip_difference": 100,
        "close_trade_at": 10,
        "close_trade_at_opposite_direction": 7,
        "pip_size": 1,
        "lot_size": 1.0
    },
    {
        "symbol": "EURUSD",
        "pip_difference": 15,
        "close_trade_at": 10,
        "close_trade_at_opposite_direction": 8,
        "pip_size": 0.0001,
        "lot_size": 1.0
    },
    {
        "symbol": "USDJPY",
        "pip_difference": 10,
        "close_trade_at": 10,
        "close_trade_at_opposite_direction": 7,
        "pip_size": 0.01,
        "lot_size": 1.0
    }
]

# Initialize MetaTrader5
if not mt5.initialize():
    print("MetaTrader5 initialization failed")
    quit()


def fetch_current_price(symbol):
    tick = mt5.symbol_info_tick(symbol)
    if tick:
        return tick.bid  # or tick.ask depending on your logic
    else:
        print(f"Failed to get current price for {symbol}")
        return None


def fetch_start_price(symbol):
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)

    start_price = None

    if now.weekday() == 0:  # Monday
        start_price = fetch_friday_closing_price(symbol)
    else:
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        utc_from = start_of_day.astimezone(pytz.utc)

        rates = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M5, utc_from, 1)

        if rates is not None and len(rates) > 0:
            start_price = rates[0]['close']
        else:
            print(f"Failed to get start price for {symbol}")
            return None

    if start_price:
        print(f"Fetched start price for {symbol}: {start_price}")

    return start_price


def fetch_friday_closing_price(symbol):
    today = datetime.now(pytz.timezone('Asia/Kolkata'))
    days_ago = (today.weekday() + 3) % 7 + 2
    last_friday = today - timedelta(days=days_ago)
    last_friday = last_friday.replace(hour=23, minute=59, second=59)
    utc_from = last_friday.astimezone(pytz.utc)

    rates = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M5, utc_from, 1)
    if rates is not None and len(rates) > 0:
        closing_price = rates[0]['close']
        print(f"Fetched last Friday's closing price for {symbol}: {closing_price}")
        return closing_price
    print(f"Failed to get last Friday's closing price for {symbol}")
    return None


def price_difference(symbol, start_price, current_price, pip_size):
    result = current_price - start_price
    if symbol == symbol:
        return result / pip_size


while True:
    counter += 1
    print(f"Running {counter}")

    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    # Clear the list at the beginning of each cycle to ensure fresh updates
    price_array_update.clear()

    for symbol in symbols_config:
        symbol_name = symbol["symbol"]
        symbol_pip_difference = symbol["pip_difference"]
        place_trade_pips = symbol["close_trade_at"]
        close_trade_at_opposite_pips = symbol["close_trade_at_opposite_direction"]
        symbol_pip_size = symbol["pip_size"]
        symbol_lot_size = symbol["lot_size"]

        current_price = fetch_current_price(symbol_name)
        start_price = fetch_start_price(symbol_name)

        # Check if start_price and current_price are valid
        if current_price is not None and start_price is not None:
            pip_difference_at_symbol = price_difference(symbol_name, start_price, current_price, symbol_pip_size)

            if pip_difference_at_symbol is not None:
                if pip_difference_at_symbol <= symbol_pip_difference:
                    direction = "sell"
                else:
                    direction = "buy"

                # Create the format dictionary correctly
                format_message = {
                    "symbol": symbol_name,
                    "current_price": current_price,
                    "start_price": start_price,
                    "pip_difference": pip_difference_at_symbol,
                    "direction": direction,
                    "timestamp": current_time
                }
                print(f"Symbol: {format_message}")

                # Check if an hour has passed since the last message was sent
                if time.time() - last_hourly_check >= 3600:
                    send_discord_message(f"Details {format_message}")
                    last_hourly_check = time.time()

    # Reset the timer for the loop interval
    start_time = time.time()

    time.sleep(1)
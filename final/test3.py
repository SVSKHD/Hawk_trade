import time
from notifications import send_discord_message
from datetime import datetime, timedelta
import pytz
import MetaTrader5 as mt5  # Ensure MetaTrader5 is imported
from db import save_or_update_threshold_in_mongo

price_array_update = []

start_time = time.time()
counter = 1

symbols_config = [
    {
        "symbol": "BTCUSD",
        "pip_difference": 15,  # Trade opens after 15 pips
        "close_trade_at": 10,  # Trade closes at 10 pips profit
        "close_trade_at_opposite_direction": 7,  # Close trade if the price reverses by 7 pips
        "pip_size": 0.0001,
        "lot_size": 1.0
    },
    {
        "symbol": "EURUSD",
        "pip_difference": 15,  # Trade opens after 15 pips
        "close_trade_at": 10,  # Trade closes at 10 pips profit
        "close_trade_at_opposite_direction": 7,  # Close trade if the price reverses by 7 pips
        "pip_size": 0.0001,
        "lot_size": 1.0
    },
    {
        "symbol": "USDJPY",
        "pip_difference": 10,  # Trade opens after 10 pips
        "close_trade_at": 10,
        "close_trade_at_opposite_direction": 7,
        "pip_size": 0.01,
        "lot_size": 1.0
    },
    # {
    #     "symbol": "GBPUSD",
    #     "pip_difference": 15,
    #     "close_trade_at": 10,
    #     "close_trade_at_opposite_direction": 7,
    #     "pip_size": 0.0001,
    #     "lot_size": 1.0
    # },
    # {
    #     "symbol": "EURJPY",
    #     "pip_difference": 10,
    #     "close_trade_at": 10,
    #     "close_trade_at_opposite_direction": 7,
    #     "pip_size": 0.01,
    #     "lot_size": 1.0
    # },
    # {
    #     "symbol": "XAGUSD",  # Silver
    #     "pip_difference": 15,
    #     "close_trade_at": 10,
    #     "close_trade_at_opposite_direction": 7,
    #     "pip_size": 0.01,
    #     "lot_size": 1.0
    # },
    # {
    #     "symbol": "XAUUSD",  # Gold
    #     "pip_difference": 15,
    #     "close_trade_at": 10,
    #     "close_trade_at_opposite_direction": 7,
    #     "pip_size": 0.01,
    #     "lot_size": 1.0
    # }
]

# Initialize MetaTrader5
if not mt5.initialize():
    print("MetaTrader5 initialization failed")
    quit()


def update_data_objects(symbol, start_price, current_price, pip_difference):
    data = {
        "symbol": symbol,
        "start_price": start_price,
        "current_price": current_price,
        "pip_difference": pip_difference
    }
    price_array_update.append(data)
    return price_array_update


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

    start_price = None  # Initialize start_price to None

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
        message = f"Fetched start price for {symbol}: {start_price}"
        print(message)

        ist_now = datetime.now(ist)
        # save_or_update_threshold_in_mongo(symbol, start_price, start_price, 0, 0, "start", [], ist_now, ist_now)

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


def price_difference(start_price, current_price):
    return current_price - start_price


while True:
    counter += 1
    print(f"running {counter}")

    if time.time() - start_time >= 60:  # Check if 1 minute has passed
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        for symbol in symbols_config:
            symbol_name = symbol["symbol"]
            opposite_direction = symbol["close_trade_at_opposite_direction"]
            profit_direction = symbol["close_trade_at"]
            current_price = fetch_current_price(symbol_name)
            start_price = fetch_start_price(symbol_name)

            if current_price is None or start_price is None:
                pip_diff = price_difference(start_price, current_price)
                format_message = {
                    "symbol": symbol_name,
                    "start_price": start_price,
                    "current_price": current_price,
                    "pip_difference": pip_diff,  # Can't calculate difference
                    "timestamp": current_time
                }
            else:
                # Calculate price difference and format the message
                pip_diff = price_difference(start_price, current_price)
                format_message = {
                    "symbol": symbol_name,
                    "start_price": start_price,
                    "current_price": current_price,
                    "pip_difference": pip_diff,
                    "timestamp": current_time
                }

            print("hello {}")
            send_discord_message(f"Details {format_message}")

        # Reset the timer
        start_time = time.time()

    time.sleep(1)
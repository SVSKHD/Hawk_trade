import time
from notifications import send_discord_message
from datetime import datetime, timedelta
import pytz
import MetaTrader5 as mt5  # Ensure MetaTrader5 is imported
from db import save_or_update_threshold_in_mongo

price_array_update = []

start_time = time.time()
last_hourly_check = time.time()
counter = 1

symbols_config = [
    {
        "symbol": "BTCUSD",
        "positive_pip_difference": 100,  # Positive threshold
        "negative_pip_difference": -100, # Negative threshold
        "close_trade_at": 10,
        "close_trade_at_opposite_direction": 7,
        "pip_size": 1,
        "lot_size": 1.0
    },
    {
        "symbol": "EURUSD",
        "positive_pip_difference": 15,
        "negative_pip_difference": -15,
        "close_trade_at": 10,
        "close_trade_at_opposite_direction": 8,
        "pip_size": 0.0001,
        "lot_size": 1.0
    },
    {
        "symbol": "USDJPY",
        "positive_pip_difference": 10,
        "negative_pip_difference": -10,
        "close_trade_at": 10,
        "close_trade_at_opposite_direction": 7,
        "pip_size": 0.01,
        "lot_size": 1.0
    }
]

# Initialize MetaTrader5
def connect_mt5():
    if not mt5.initialize():
        print("Failed to initialize MetaTrader5")
        return False
    login = 213171528  # Login provided
    password = "AHe@Yps3"  # Password provided
    server = "OctaFX-Demo"  # Server provided

    authorized = mt5.login(login, password=password, server=server)
    if not authorized:
        print(f"Login failed for account {login}")
        return False
    print(f"Successfully logged into account {login} on server {server}")
    return True


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


def price_difference(start_price, current_price, pip_size):
    return (current_price - start_price) / pip_size


def main():
    global last_hourly_check, counter  # Declare global variables

    if connect_mt5():
        while True:
            counter += 1
            print(f"Running {counter}")

            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

            # Clear the list at the beginning of each cycle to ensure fresh updates
            price_array_update.clear()

            # Accumulate messages for all symbols
            messages = []

            for symbol in symbols_config:
                symbol_name = symbol["symbol"]
                positive_pip_difference = symbol["positive_pip_difference"]
                negative_pip_difference = symbol["negative_pip_difference"]
                symbol_pip_size = symbol["pip_size"]

                current_price = fetch_current_price(symbol_name)
                start_price = fetch_start_price(symbol_name)

                # Check if start_price and current_price are valid
                if current_price is not None and start_price is not None:
                    pip_difference_at_symbol = price_difference(start_price, current_price, symbol_pip_size)

                    # Determine if the pip difference exceeds either the positive or negative threshold
                    if pip_difference_at_symbol >= positive_pip_difference:
                        direction = "buy"
                        movement = f"+{pip_difference_at_symbol:.2f} pips (exceeds +{positive_pip_difference} pips)"
                    elif pip_difference_at_symbol <= negative_pip_difference:
                        direction = "sell"
                        movement = f"{pip_difference_at_symbol:.2f} pips (exceeds {negative_pip_difference} pips)"
                    else:
                        direction = "hold"
                        movement = f"{pip_difference_at_symbol:.2f} pips (within range)"

                    # Create the format dictionary for log message
                    format_message = (
                        f"Symbol: {symbol_name}, Current Price: {current_price}, "
                        f"Start Price: {start_price}, Pip Difference: {movement}, "
                        f"Direction: {direction}, Time: {current_time}"
                    )

                    # Add message to the list if there's significant movement
                    if direction != "hold":
                        messages.append(format_message)

            # Send all messages to Discord if there are significant movements and time interval is met
            if messages and time.time() - last_hourly_check >= 60:
                combined_message = "\n".join(messages)
                send_discord_message(combined_message)
                last_hourly_check = time.time()

            time.sleep(1)  # Sleep for 1 second to prevent tight loop

if __name__ == "__main__":
    main()

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
        "positive_pip_difference": 50,  # Reduced threshold for testing
        "negative_pip_difference": -50,
        "close_trade_at": 10,
        "close_trade_at_opposite_direction": 7,
        "pip_size": 1,
        "lot_size": 1.0
    },
    {
        "symbol": "EURUSD",
        "positive_pip_difference": 1,  # Reduced threshold for testing
        "negative_pip_difference": -1,
        "close_trade_at": 10,
        "close_trade_at_opposite_direction": 8,
        "pip_size": 0.0001,
        "lot_size": 1.0
    },
    {
        "symbol": "USDJPY",
        "positive_pip_difference": 1,  # Reduced threshold for testing
        "negative_pip_difference": -1,
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
    login = 213171528  # Replace with your login
    password = "AHe@Yps3"  # Replace with your password
    server = "OctaFX-Demo"  # Replace with your server

    authorized = mt5.login(login, password=password, server=server)
    if not authorized:
        print(f"Login failed for account {login}")
        return False
    print(f"Successfully logged into account {login} on server {server}")
    return True

def check_symbol_availability(symbol):
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"Symbol {symbol} not found, cannot proceed")
        return False
    if not symbol_info.visible:
        if not mt5.symbol_select(symbol, True):
            print(f"Failed to select {symbol}")
            return False
    return True

def fetch_current_price(symbol):
    if not mt5.symbol_select(symbol, True):
        print(f"Failed to select symbol {symbol}")
        return None
    tick = mt5.symbol_info_tick(symbol)
    if tick:
        print(f"Current price for {symbol}: {tick.bid}")
        return tick.bid  # or tick.ask depending on your logic
    else:
        print(f"Failed to get current price for {symbol}")
        return None

def fetch_start_price(symbol):
    if not mt5.symbol_select(symbol, True):
        print(f"Failed to select symbol {symbol}")
        return None
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
            print(f"Start price for {symbol}: {start_price}")
        else:
            print(f"Failed to get start price for {symbol}")
            return None

    return start_price

def fetch_friday_closing_price(symbol):
    if not mt5.symbol_select(symbol, True):
        print(f"Failed to select symbol {symbol}")
        return None
    today = datetime.now(pytz.timezone('Asia/Kolkata'))
    days_ago = (today.weekday() + 3) % 7 + 2
    last_friday = today - timedelta(days=days_ago)
    last_friday = last_friday.replace(hour=23, minute=59, second=59, microsecond=0)
    utc_from = last_friday.astimezone(pytz.utc)

    rates = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M5, utc_from, 1)
    if rates is not None and len(rates) > 0:
        closing_price = rates[0]['close']
        print(f"Fetched last Friday's closing price for {symbol}: {closing_price}")
        return closing_price
    print(f"Failed to get last Friday's closing price for {symbol}")
    return None

def price_difference(start_price, current_price, pip_size):
    result=(current_price - start_price)
    final_result = result / pip_size
    print("result", final_result)
    return result

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

                # Check symbol availability
                if not check_symbol_availability(symbol_name):
                    continue  # Skip to the next symbol

                current_price = fetch_current_price(symbol_name)
                start_price = fetch_start_price(symbol_name)

                # Check if start_price and current_price are valid
                if current_price is not None and start_price is not None:
                    pip_difference_at_symbol = price_difference(start_price, current_price, symbol_pip_size)
                    print(f"Symbol: {symbol_name}, Pip Difference: {pip_difference_at_symbol}")

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

                    # Always add message to the list for debugging
                    messages.append(format_message)
                else:
                    print(f"Skipping symbol {symbol_name} due to missing data.")

            # Send all messages to Discord if time interval is met
            if messages and time.time() - last_hourly_check >= 60:
                combined_message = "\n".join(messages)
                send_discord_message(combined_message)
                last_hourly_check = time.time()

            time.sleep(1)  # Sleep for 1 second to prevent tight loop

if __name__ == "__main__":
    main()

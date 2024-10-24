# main.py
import MetaTrader5 as mt5
import pytz
from datetime import datetime, timedelta
import time
from notifications import send_discord_message
from db import save_or_update_threshold_in_mongo, load_symbol_data

# Initialize start_prices dictionary to keep track of prices for the current day
start_prices = {}

# Initialize a trade_count dictionary to track trades placed for each symbol
trade_count = {}

# Set the maximum number of trades allowed per day
MAX_TRADES_PER_DAY = 2

# Track the date of the last trade reset
last_trade_reset = None


# Connect to MetaTrader 5
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


# Fetch the start price at 12 AM using the M5 timeframe, or fetch Friday’s closing price on Monday
def fetch_start_prices(symbols_config):
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)

    global start_prices  # Use global to update the start prices dictionary

    for config in symbols_config:
        symbol = config['symbol']
        if now.weekday() == 0:  # If today is Monday, get Friday's closing price
            start_price = fetch_friday_closing_price(symbol)
        else:
            # Fetch the 12 AM price even if the script starts later in the day
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            rates = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M5, start_of_day, 1)
            if rates:
                start_price = rates[0]['close']

        # If a start price is successfully fetched, update the dictionary
        if start_price:
            start_prices[symbol] = start_price
            message = f"Fetched start price for {symbol}: {start_price}"
            send_discord_message(message)

    return start_prices


# Fetch previous Friday’s closing price using the 5-minute timeframe for Monday
def fetch_friday_closing_price(symbol):
    today = datetime.now(pytz.timezone('Asia/Kolkata'))
    days_ago = (today.weekday() + 3) % 7 + 2  # Calculate how many days back to get to last Friday
    last_friday = today - timedelta(days=days_ago)
    last_friday = last_friday.replace(hour=23, minute=59, second=59)

    # Fetch the last 5-minute candle of last Friday
    rates = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M5, last_friday, 1)
    if rates:
        closing_price = rates[0]['close']
        print(f"Fetched last Friday's closing price for {symbol}: {closing_price}")
        return closing_price
    return None


# Calculate the pip difference and determine the direction
def calculate_pip_difference(start_price, current_price, config):
    pip_size = config['pip_size']

    # Calculate the pip difference
    pip_difference = (current_price - start_price) / pip_size

    # Determine direction
    direction = 'up' if pip_difference > 0 else 'down'

    return pip_difference, direction  # Return only pip_difference and direction


# Reset the trade count at the start of each day
def reset_trade_count_daily():
    """Resets the trade count at the start of a new trading day."""
    global trade_count, last_trade_reset

    # Get the current time in IST
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)

    # Check if we need to reset trade count (new day)
    if last_trade_reset is None or now.date() > last_trade_reset.date():
        trade_count = {symbol: 0 for symbol in trade_count}  # Reset the trade count for all symbols
        last_trade_reset = now  # Update the last reset time
        print("Trade counts reset for a new day.")


# Check if the pip difference hits the threshold and handle trade logic
def check_threshold(config, pip_difference, direction, trade_status, current_price):
    symbol = config['symbol']
    threshold = config['pip_difference']
    close_trade_at = config['close_trade_at']
    close_trade_opposite = config['close_trade_at_opposite_direction']
    lot_size = config['lot_size']

    # Tolerance for sudden price movements
    tolerance = 0.5

    # Minimum and maximum pip range for closing
    min_pips = 7
    max_pips = 11

    # 70% of close_trade_at threshold
    close_threshold_70 = close_trade_at * 0.7

    # Reset the trade count at the start of each new day
    reset_trade_count_daily()

    # Initialize trade count if not present
    if symbol not in trade_count:
        trade_count[symbol] = 0

    # Check if the maximum number of trades has been reached for the day
    if trade_count[symbol] >= MAX_TRADES_PER_DAY:
        print(f"Max trades reached for {symbol}. No further trades will be placed today.")
        return

    # Check if a trade has already been placed (to prevent duplicate trades)
    if trade_status['trade_placed']:
        print(f"Trade already placed for {symbol}, no new trades will be placed until it's closed.")
        return

    # Open a trade if the pip_difference threshold is reached or exceeded
    if direction == 'up' and pip_difference >= threshold - tolerance and not trade_status['trade_placed'] and trade_count[symbol] < MAX_TRADES_PER_DAY:
        place_trade(symbol, 'buy', lot_size, current_price)
        trade_status['trade_placed'] = True
        trade_status['trade_opened_at'] = pip_difference  # Track where the trade was opened
        trade_count[symbol] += 1  # Increment the trade count for this symbol
        return

    elif direction == 'down' and pip_difference <= -threshold + tolerance and not trade_status['trade_placed'] and trade_count[symbol] < MAX_TRADES_PER_DAY:
        place_trade(symbol, 'sell', lot_size, current_price)
        trade_status['trade_placed'] = True
        trade_status['trade_opened_at'] = pip_difference  # Track where the trade was opened
        trade_count[symbol] += 1  # Increment the trade count for this symbol
        return

    # Handle closing trades dynamically here
    # ...


# Placeholder for placing trade
def place_trade(symbol, action, lot_size, current_price):
    message = f"Placing {action} trade for {symbol} with {lot_size} lots at ${current_price}"
    print(message)
    send_discord_message(message)


# Placeholder for closing trade
def close_trade(symbol, current_price):
    message = f"Closing trade for {symbol} at {current_price}"
    print(message)
    send_discord_message(message)


def fetch_current_price(symbol):
    # Fetch current price using MetaTrader 5 API
    tick = mt5.symbol_info_tick(symbol)
    if tick:
        return tick.bid  # or tick.ask depending on your logic


# Fetch the start prices for symbols and calculate thresholds
def main():
    symbols_config = [
        {
            "symbol": "EURUSD",
            "pip_difference": 15,  # Trade opens after 15 pips
            "close_trade_at": 10,  # Trade closes at 10 pips profit
            "close_trade_at_opposite_direction": 7,  # Close trade if the price reverses by 7 pips
            "pip_size": 0.0001,
            "lot_size": 10  # Trading 10 lots
        },
        {
            "symbol": "USDJPY",
            "pip_difference": 10,  # Trade opens after 10 pips (different pip difference for USDJPY)
            "close_trade_at": 10,  # Trade closes at 10 pips profit
            "close_trade_at_opposite_direction": 7,  # Close trade if the price reverses by 7 pips
            "pip_size": 0.01,  # Pip size for USDJPY is typically 0.01
            "lot_size": 10  # Trading 10 lots
        }
    ]

    global start_prices
    trade_status = {symbol['symbol']: {'trade_placed': False, 'cooldown_until': 0} for symbol in symbols_config}

    # Connect to MetaTrader 5
    if not connect_mt5():
        return

    # Fetch the start prices once at the beginning of the script
    if not start_prices:
        start_prices = fetch_start_prices(symbols_config)

    while True:
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)

        if not start_prices:  # Fetch start prices for the day if not already fetched
            print("Fetching start prices...")
            start_prices = fetch_start_prices(symbols_config)
            if start_prices:
                print(f"Start prices fetched: {start_prices}")

        # Once start prices are fetched, calculate pip differences and check thresholds
        if start_prices:
            for config in symbols_config:
                symbol = config['symbol']
                current_price = fetch_current_price(symbol)
                if current_price is not None:
                    start_price = start_prices.get(symbol)
                    if start_price:
                        pip_difference, direction = calculate_pip_difference(start_price, current_price, config)

                        # Print the pip difference and direction for verification
                        print(f"{symbol}: Start Price = {start_price}, Current Price = {current_price}, Pip Difference = {pip_difference:.2f}, Direction = {direction}")

                        # Check if a cooldown is in place before executing trade logic
                        if time.time() > trade_status[symbol]['cooldown_until']:
                            check_threshold(config, pip_difference, direction, trade_status[symbol], current_price)

        time.sleep(60)  # Check every minute


# Run the script
if __name__ == "__main__":
    main()

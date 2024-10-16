import MetaTrader5 as mt5
import pytz
from datetime import datetime, timedelta
import time
from notifications import send_discord_message
# Initialize start_prices dictionary to keep track of prices for the current day
start_prices = {}


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
            message=f"Fetched start price for {symbol}: {start_price}"
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
    return pip_difference, direction


# Check if the pip difference hits the threshold and handle trade logic
def check_threshold(config, pip_difference, direction, trade_status):
    symbol = config['symbol']
    threshold = config['pip_difference']
    close_trade_at = config['close_trade_at']
    close_trade_opposite = config['close_trade_at_opposite_direction']
    lot_size = config['lot_size']

    # Open a trade if the pip_difference threshold is reached
    if direction == 'up' and pip_difference >= threshold and not trade_status['trade_placed']:
        place_trade(symbol, 'buy', lot_size)
        trade_status['trade_placed'] = True

    elif direction == 'down' and pip_difference <= -threshold and not trade_status['trade_placed']:
        place_trade(symbol, 'sell', lot_size)
        trade_status['trade_placed'] = True

    # Monitor the trade and close when the `close_trade_at` or `close_trade_opposite_direction` is hit
    if trade_status['trade_placed']:
        if (direction == 'up' and pip_difference >= close_trade_at) or \
                (direction == 'down' and pip_difference <= -close_trade_at):
            close_trade(symbol)
            trade_status['trade_placed'] = False
        elif (direction == 'down' and pip_difference <= -close_trade_opposite) or \
                (direction == 'up' and pip_difference >= close_trade_opposite):
            close_trade(symbol)
            trade_status['trade_placed'] = False


# Placeholder for placing trade
def place_trade(symbol, action, lot_size):
    print(f"Placing {action} trade for {symbol} with {lot_size} lots")
    # You would add actual MetaTrader 5 API calls here to place the trade with the given lot size
    pass


# Placeholder for closing trade
def close_trade(symbol):
    print(f"Closing trade for {symbol}")
    # Use MetaTrader 5 API to close the trade
    pass


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
    trade_status = {symbol['symbol']: {'trade_placed': False} for symbol in symbols_config}

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
                        print(
                            f"{symbol}: Start Price = {start_price}, Current Price = {current_price}, Pip Difference = {pip_difference:.2f}, Direction = {direction}")

                        check_threshold(config, pip_difference, direction, trade_status[symbol])

        time.sleep(1)  # Check every minute


# Run the script
if __name__ == "__main__":
    main()

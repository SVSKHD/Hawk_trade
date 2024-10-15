# main.py
import MetaTrader5 as mt5
import pytz
from datetime import datetime, timedelta
import time
from notifications import send_discord_message
from db import save_or_update_threshold_in_mongo
from trade_management import close_trades_by_symbol

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

        # If a start price is successfully fetched, update the dictionary and save to MongoDB
        if start_price:
            start_prices[symbol] = start_price
            message = f"Fetched start price for {symbol}: {start_price}"
            send_discord_message(message)

            # Save start price to MongoDB
            save_or_update_threshold_in_mongo(symbol, start_price, start_price, 0, 0, "start", [], datetime.now(ist), datetime.now(ist))  # Saving start price

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


# Check if the pip difference hits the threshold and handle trade logic (place and close trades)
def check_threshold(config, pip_difference, direction, trade_status, current_price):
    symbol = config['symbol']
    threshold = config['pip_difference']
    close_trade_at = config['close_trade_at']
    close_trade_opposite = config['close_trade_at_opposite_direction']
    lot_size = config['lot_size']

    # Tolerance for sudden price movements
    tolerance = 0.5

    # Reset the trade count at the start of each new day
    reset_trade_count_daily()

    # Initialize trade count if not present
    if symbol not in trade_count:
        trade_count[symbol] = 0

    # Check if the maximum number of trades has been reached for the day
    if trade_count[symbol] >= MAX_TRADES_PER_DAY:
        print(f"Max trades reached for {symbol}. No further trades will be placed today.")
        return

    # Handle trade placement
    if not trade_status['trade_placed']:
        # Place trade if the pip difference threshold is reached or exceeded
        if direction == 'up' and pip_difference >= threshold - tolerance:
            place_trade_notify(symbol, 'buy', lot_size)
            trade_status['trade_placed'] = True
            trade_status['trade_opened_at'] = pip_difference  # Track where the trade was opened
            trade_count[symbol] += 1  # Increment the trade count for this symbol

            # Save threshold hit to MongoDB
            save_or_update_threshold_in_mongo(
                symbol,
                start_prices[symbol],
                current_price,
                trade_status['trade_opened_at'],
                pip_difference,
                direction,
                [pip_difference],
                datetime.now(),
                datetime.now()
            )
            return

        elif direction == 'down' and pip_difference <= -threshold + tolerance:
            place_trade_notify(symbol, 'sell', lot_size)
            trade_status['trade_placed'] = True
            trade_status['trade_opened_at'] = pip_difference  # Track where the trade was opened
            trade_count[symbol] += 1  # Increment the trade count for this symbol

            # Save threshold hit to MongoDB
            save_or_update_threshold_in_mongo(
                symbol,
                start_prices[symbol],
                current_price,
                trade_status['trade_opened_at'],
                pip_difference,
                direction,
                [pip_difference],
                datetime.now(),
                datetime.now()
            )
            return

    # Handle trade closing
    if trade_status['trade_placed']:
        trade_opened_at = trade_status['trade_opened_at']

        # Close trade at profit target
        if (direction == 'up' and pip_difference >= trade_opened_at + close_trade_at) or \
                (direction == 'down' and pip_difference <= trade_opened_at - close_trade_at):
            close_trade_notify(symbol, current_price)
            trade_status['trade_placed'] = False
            trade_status['cooldown_until'] = time.time() + 60  # Cooldown after closing a trade
            print(f"Trade closed for {symbol} at {current_price} due to reaching profit target.")
            return

        # Close trade if the price reverses beyond a certain threshold (stop-loss)
        if (direction == 'up' and pip_difference <= trade_opened_at - close_trade_opposite) or \
                (direction == 'down' and pip_difference >= trade_opened_at + close_trade_opposite):
            close_trade_notify(symbol, current_price)
            trade_status['trade_placed'] = False
            trade_status['cooldown_until'] = time.time() + 60  # Cooldown after closing a trade
            print(f"Trade closed for {symbol} at {current_price} due to price reversal.")
            return

    # Handle trade closing
    if trade_status['trade_placed']:
        trade_opened_at = trade_status['trade_opened_at']
        # Close trade at profit target
        if (direction == 'up' and pip_difference >= trade_opened_at + close_trade_at) or \
           (direction == 'down' and pip_difference <= trade_opened_at - close_trade_at):
            close_trade_notify(symbol, current_price)
            trade_status['trade_placed'] = False
            trade_status['cooldown_until'] = time.time() + 60  # Cooldown of 60 seconds after closing a trade
            print(f"Trade closed for {symbol} at {current_price} due to reaching profit target.")
            return

        # Close trade if the price reverses (opposite direction) beyond a certain threshold
        if (direction == 'down' and pip_difference <= trade_opened_at - close_trade_opposite) or \
           (direction == 'up' and pip_difference >= trade_opened_at + close_trade_opposite):
            close_trade_notify(symbol, current_price)
            trade_status['trade_placed'] = False
            trade_status['cooldown_until'] = time.time() + 60  # Cooldown of 60 seconds after closing a trade
            print(f"Trade closed for {symbol} at {current_price} due to opposite direction movement.")
            return


# Placeholder for placing trade
def place_trade_notify(symbol, action, lot_size):
    # Ensure MT5 is initialized
    if not mt5.initialize():
        print("Failed to initialize MetaTrader 5")
        return

    print(f"Initialized MetaTrader 5 for trading with symbol {symbol}")

    # Check for initialization errors
    print(f"Initialization error: {mt5.last_error()}")

    # Ensure the symbol is available
    if not mt5.symbol_select(symbol, True):
        print(f"Failed to select symbol {symbol}")
        mt5.shutdown()
        return

    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"Symbol info not available for {symbol}")
        mt5.shutdown()
        return

    # Get the latest price for the symbol
    price_info = mt5.symbol_info_tick(symbol)
    if price_info is None:
        print(f"Failed to get tick information for {symbol}")
        mt5.shutdown()
        return

    # Set price based on buy or sell action
    price = price_info.bid
    print(f"Price for {action}: {price}")

    # Define request parameters
    lot = lot_size if lot_size is not None else 1.0
    deviation = 50  # Increase deviation to account for price changes
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
        "type_filling": mt5.ORDER_FILLING_FOK,  # Try ORDER_FILLING_IOC
    }

    print("Request parameters:", request)

    # Send the trade request
    result = mt5.order_send(request)

    # Check the result and print details
    if result is None:
        print("Order send failed: no result returned")
        send_discord_message(f"Order send error when it is none for clear error description: {mt5.last_error()}")
    else:
        print("Order send result:")
        print(f"  retcode: {result.retcode}")
        print(f"  deal: {result.deal}")
        print(f"  order: {result.order}")
        print(f"  price: {result.price}")
        print(f"  comment: {result.comment}")
        print(f"  request_id: {result.request_id}")
        print(f"  bid: {result.bid}")
        print(f"  ask: {result.ask}")
        print(f"  volume: {result.volume}")
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"Trade request failed, retcode={result.retcode}")
        else:
            now = datetime.now()
            send_discord_message(f"Trade executed successfully at {now}, order={result}")

    # Shutdown the connection
    mt5.shutdown()

    # # Assuming send_discord_message is defined somewhere in your code
    # send_discord_message(message)  # Send the notification to Discord


# Placeholder for closing trade
def close_trade_notify(symbol, current_price):
    close_status = close_trades_by_symbol(symbol)
    message = f"Closing trade for {symbol} at {current_price} status {close_status}"
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
        "pip_difference": 10,  # Trade opens after 10 pips
        "close_trade_at": 10,  # Trade closes at 10 pips profit
        "close_trade_at_opposite_direction": 7,  # Close trade if the price reverses by 7 pips
        "pip_size": 0.01,  # Pip size for USDJPY is typically 0.01
        "lot_size": 10  # Trading 10 lots
    },
    {
        "symbol": "GBPUSD",
        "pip_difference": 15,  # Same as EURUSD
        "close_trade_at": 10,  # Trade closes at 10 pips profit
        "close_trade_at_opposite_direction": 7,  # Close trade if the price reverses by 7 pips
        "pip_size": 0.0001,
        "lot_size": 10  # Trading 10 lots
    },
    {
        "symbol": "EURJPY",
        "pip_difference": 10,  # Same as USDJPY
        "close_trade_at": 10,  # Trade closes at 10 pips profit
        "close_trade_at_opposite_direction": 7,  # Close trade if the price reverses by 7 pips
        "pip_size": 0.01,  # Same pip size as USDJPY
        "lot_size": 10  # Trading 10 lots
    },
    {
        "symbol": "XAGUSD",  # Silver
        "pip_difference": 15,  # Trade opens after 15 pips
        "close_trade_at": 10,  # Trade closes at 10 pips profit
        "close_trade_at_opposite_direction": 7,  # Close trade if the price reverses by 7 pips
        "pip_size": 0.01,  # Silver's pip size
        "lot_size": 10  # Trading 10 lots
    },
    {
        "symbol": "XAUUSD",  # Gold
        "pip_difference": 15,  # Trade opens after 15 pips
        "close_trade_at": 10,  # Trade closes at 10 pips profit
        "close_trade_at_opposite_direction": 7,  # Close trade if the price reverses by 7 pips
        "pip_size": 0.01,  # Gold's pip size
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

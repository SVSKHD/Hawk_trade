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
        start_price = None  # Initialize start_price to None
        if now.weekday() == 0:  # If today is Monday, get Friday's closing price
            start_price = fetch_friday_closing_price(symbol)
        else:
            # Fetch the 12 AM price even if the script starts later in the day
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            utc_from = start_of_day.astimezone(pytz.utc)
            rates = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M5, utc_from, 1)
            if rates is not None and len(rates) > 0:
                start_price = rates[0]['close']
            else:
                print(f"Failed to get start price for {symbol}")
                continue

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
    utc_from = last_friday.astimezone(pytz.utc)

    # Fetch the last 5-minute candle of last Friday
    rates = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M5, utc_from, 1)
    if rates is not None and len(rates) > 0:
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
            trade_status['trade_opened_at'] = pip_difference
            trade_status['trade_direction'] = 'buy'
            trade_count[symbol] += 1
            return
        elif direction == 'down' and pip_difference <= -threshold + tolerance:
            place_trade_notify(symbol, 'sell', lot_size)
            trade_status['trade_placed'] = True
            trade_status['trade_opened_at'] = pip_difference
            trade_status['trade_direction'] = 'sell'
            trade_count[symbol] += 1
            return

    # Handle trade closing
    if trade_status['trade_placed']:
        trade_opened_at = trade_status['trade_opened_at']
        trade_direction = trade_status['trade_direction']

        # Calculate profit/loss pip difference from trade open point
        if trade_direction == 'buy':
            profit_pip_difference = pip_difference - trade_opened_at
        else:  # trade_direction == 'sell'
            profit_pip_difference = trade_opened_at - pip_difference

        # Close trade at profit target
        if profit_pip_difference >= close_trade_at:
            close_trade_notify(symbol, current_price)
            trade_status['trade_placed'] = False
            trade_status['cooldown_until'] = time.time() + 60
            print(f"Trade closed for {symbol} at {current_price} due to reaching profit target.")
            return

        # Close trade if the price reverses beyond stop-loss threshold
        if profit_pip_difference <= -close_trade_opposite:
            close_trade_notify(symbol, current_price)
            trade_status['trade_placed'] = False
            trade_status['cooldown_until'] = time.time() + 60
            print(f"Trade closed for {symbol} at {current_price} due to hitting stop loss.")
            return

# Function to place trade and send notifications
def place_trade_notify(symbol, action, lot_size):
    # Ensure MT5 is initialized
    if not mt5.initialize():
        print("Failed to initialize MetaTrader 5")
        return

    print(f"Initialized MetaTrader 5 for trading with symbol {symbol}")

    # Ensure the symbol is available
    if not mt5.symbol_select(symbol, True):
        print(f"Failed to select symbol {symbol}")
        mt5.shutdown()
        return

    # Get the latest price for the symbol
    price_info = mt5.symbol_info_tick(symbol)
    if price_info is None:
        print(f"Failed to get tick information for {symbol}")
        mt5.shutdown()
        return

    # Set price based on buy or sell action
    price = price_info.ask if action == 'buy' else price_info.bid
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
        "type_filling": mt5.ORDER_FILLING_FOK,  # You can also try mt5.ORDER_FILLING_IOC
    }

    print("Request parameters:", request)

    # Send the trade request
    result = mt5.order_send(request)

    # Check the result and print details
    if result is None:
        print("Order send failed: no result returned")
        send_discord_message(f"Order send error: {mt5.last_error()}")
    else:
        print("Order send result:")
        print(f"  retcode: {result.retcode}")
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"Trade request failed, retcode={result.retcode}")
            send_discord_message(f"Trade request failed for {symbol}, retcode={result.retcode}")
        else:
            now = datetime.now()
            send_discord_message(f"Trade executed successfully at {now}, order={result}")

# Function to close trade and send notifications
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
    else:
        print(f"Failed to get current price for {symbol}")
        return None

# Fetch the start prices for symbols and calculate thresholds
def main():
    symbols_config = [
        {
            "symbol": "EURUSD",
            "pip_difference": 15,  # Trade opens after 15 pips
            "close_trade_at": 10,  # Trade closes at 10 pips profit
            "close_trade_at_opposite_direction": 7,  # Close trade if the price reverses by 7 pips
            "pip_size": 0.0001,
            "lot_size": 1.0  # Trading 1 lot
        },
        {
            "symbol": "USDJPY",
            "pip_difference": 10,  # Trade opens after 10 pips
            "close_trade_at": 10,
            "close_trade_at_opposite_direction": 7,
            "pip_size": 0.01,
            "lot_size": 1.0
        },
        {
            "symbol": "GBPUSD",
            "pip_difference": 15,  # Same as EURUSD
            "close_trade_at": 10,
            "close_trade_at_opposite_direction": 7,
            "pip_size": 0.0001,
            "lot_size": 1.0
        },
        {
            "symbol": "EURJPY",
            "pip_difference": 10,  # Same as USDJPY
            "close_trade_at": 10,
            "close_trade_at_opposite_direction": 7,
            "pip_size": 0.01,
            "lot_size": 1.0
        },
        {
            "symbol": "XAGUSD",  # Silver
            "pip_difference": 15,
            "close_trade_at": 10,
            "close_trade_at_opposite_direction": 7,
            "pip_size": 0.01,
            "lot_size": 1.0
        },
        {
            "symbol": "XAUUSD",  # Gold
            "pip_difference": 15,
            "close_trade_at": 10,
            "close_trade_at_opposite_direction": 7,
            "pip_size": 0.01,
            "lot_size": 1.0
        }
    ]

    global start_prices
    trade_status = {config['symbol']: {'trade_placed': False, 'cooldown_until': 0} for config in symbols_config}

    # Connect to MetaTrader 5
    if not connect_mt5():
        return

    # Fetch the start prices once at the beginning of the script
    if not start_prices:
        start_prices = fetch_start_prices(symbols_config)

    # Time when the last Discord message was sent
    last_discord_message_time = time.time()

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

        # At the end of the loop, check if it's time to send the hourly update
        if time.time() - last_discord_message_time >= 3600:
            message_data = []
            for config in symbols_config:
                symbol = config['symbol']
                start_price = start_prices.get(symbol)
                current_price = fetch_current_price(symbol)
                if start_price is None or current_price is None:
                    continue
                pip_difference, direction = calculate_pip_difference(start_price, current_price, config)
                trade_status_symbol = trade_status[symbol]
                if trade_status_symbol['trade_placed']:
                    trade_info = f"Trade is placed and running at {current_price}"
                else:
                    trade_info = "No trade placed"
                symbol_data = {
                    'symbol': symbol,
                    'start_price': start_price,
                    'current_price': current_price,
                    'pip_difference': round(pip_difference, 2),
                    'trade_status': trade_info
                }
                message_data.append(symbol_data)
            # Format the message
            message = "Hourly Update:\n"
            for data in message_data:
                message += (
                    f"Symbol: {data['symbol']}, Start Price: {data['start_price']}, "
                    f"Current Price: {data['current_price']}, Pip Difference: {data['pip_difference']}, "
                    f"Trade Status: {data['trade_status']}\n"
                )
            # Send the message to Discord
            send_discord_message(message)
            last_discord_message_time = time.time()

        time.sleep(60)  # Check every minute

# Run the script
if __name__ == "__main__":
    main()
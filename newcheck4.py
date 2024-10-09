import MetaTrader5 as mt5
from datetime import datetime, timedelta
import pytz


# Function to initialize MetaTrader 5
def initialize_mt5():
    # Initialize MetaTrader 5
    if not mt5.initialize():
        print("MetaTrader 5 initialization failed")
        mt5.shutdown()
        return False
    print("MetaTrader 5 initialized successfully")
    return True


# Function to get the last Friday's closing price using bar data with IST timezone
def get_last_friday_closing(symbol):
    # Define timezone for IST
    timezone = pytz.timezone('Asia/Kolkata')

    # Get the current time in IST
    now = datetime.now(tz=timezone)

    # Calculate the last Friday
    offset = (now.weekday() + 2) % 7  # Friday is 4 (Python's weekday, Monday = 0)
    last_friday = now - timedelta(days=offset)

    # Set the closing time at 23:59:00 IST on last Friday
    friday_close_time = datetime(last_friday.year, last_friday.month, last_friday.day, 23, 59, tzinfo=timezone)
    friday_start_time = datetime(last_friday.year, last_friday.month, last_friday.day, 0, 0, tzinfo=timezone)

    # Fetch 1-minute bars from midnight to the market close on Friday (in IST)
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M5, friday_start_time, friday_close_time)

    if rates is not None and len(rates) > 0:
        last_rate = rates[-1]  # Get the last bar before the market closes
        closing_price = last_rate['close']  # Close price of the last 1-minute bar
        return closing_price, last_friday.strftime('%Y-%m-%d')
    else:
        return None, "No data found"


# Main function to fetch and display Friday's closing price
def main():
    # Initialize MT5 connection
    if not initialize_mt5():
        return

    # Symbol to fetch the Friday closing price for
    symbol = "EURJPY"  # You can replace this with other symbols like 'GBPUSD', 'USDJPY', etc.

    # Get the last Friday's closing price in IST
    closing_price, date = get_last_friday_closing(symbol)

    if closing_price:
        print(f"The closing price for {symbol} on {date} (IST) was {closing_price}")
    else:
        print(f"Failed to retrieve the closing price for {symbol} on {date}")

    # Shutdown MetaTrader 5 after use
    mt5.shutdown()


# Entry point of the script
if __name__ == "__main__":
    main()

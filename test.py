import MetaTrader5 as mt5
from datetime import datetime, timezone
import pytz


def initialize_mt5():
    if not mt5.initialize():
        print("Failed to initialize MetaTrader 5")
        quit()


def get_mt5_server_time():
    # Get the current server time by requesting the tick data of a common symbol
    symbol = "EURUSD"  # You can replace this with any symbol available on your account
    tick = mt5.symbol_info_tick(symbol)

    if tick is None:
        print(f"Failed to retrieve tick data for {symbol}.")
        return

    # Get the server time from the tick data (Unix timestamp)
    server_time_unix = tick.time
    # Use timezone-aware objects to avoid deprecation warnings
    server_time_utc = datetime.fromtimestamp(server_time_unix, tz=timezone.utc)  # Convert to UTC datetime

    # Get local system time and make it timezone-aware (assuming your local timezone)
    local_timezone = pytz.timezone('Asia/Kolkata')  # Replace with your local timezone, if different
    local_time = datetime.now(local_timezone)  # Local system time with timezone info

    print(f"Server time (UTC) from {symbol}: {server_time_utc}")
    print(f"Local system time: {local_time}")

    # Calculate the difference between local time and server time
    time_difference = local_time - server_time_utc
    time_difference_abs = abs(time_difference)  # Use absolute difference to avoid negative days

    # Display hours and minutes for the time difference
    hours, remainder = divmod(time_difference_abs.total_seconds(), 3600)
    minutes, _ = divmod(remainder, 60)

    print(f"Difference between local system time and server time: {int(hours)} hours, {int(minutes)} minutes")

    return server_time_utc


def main():
    initialize_mt5()
    get_mt5_server_time()


if __name__ == "__main__":
    main()

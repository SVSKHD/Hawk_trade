import MetaTrader5 as mt5
import os
import json
from datetime import date, timedelta, datetime, time as dt_time
import pytz
import time

from utils import initialize_mt5, get_tick_values, get_last_friday, get_last_friday_closing

# Create the full path to details.json
current_dir = os.path.dirname(os.path.abspath(__file__))
details_path = os.path.join(current_dir, 'details.json')

# Load details from details.json
with open(details_path) as f:
    config = json.load(f)

symbols = config['symbols']


# Function to check if the given date is Monday
def check_day(given_date=None):
    if given_date is None:
        given_date = date.today()

    if given_date.weekday() == 0:  # Monday is represented by 0
        print(f"Today is Monday: {given_date}")
        return True, given_date
    else:
        print(f"Today is not Monday: {given_date}")
        return False, given_date


# Correct date initialization for a specific date
specific_date = date(2024, 10, 7)

timezone = pytz.timezone("Asia/Kolkata")
def main():
    monday, given_date = check_day(specific_date)
    initialize_mt5()  # Initialize MetaTrader 5 before use

    if monday:
        print(f"It's Monday: {given_date}")
        friday = get_last_friday()  # Retrieve the previous Friday
        print(f"Last Friday was: {friday}")

        # Get tick data for each symbol in the config
        for sym in symbols:
            symbol_data = sym['symbol']
            start_price=get_last_friday_closing(symbol_data)
            print(symbol_data, start_price)


    else:
        print(f"It's not Monday: {given_date}")


# Call the main function
if __name__ == '__main__':
    main()

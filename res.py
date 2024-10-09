import os
import json
from datetime import date, timedelta, datetime
import MetaTrader5 as mt5

from utils import initialize_mt5, get_tick_values, get_last_friday

current_dir = os.path.dirname(os.path.abspath(__file__))

# Create the full path to details.json
details_path = os.path.join(current_dir, 'details.json')

# Load details from details.json
with open(details_path) as f:
    config = json.load(f)

symbols = config['symbols']

def check_day(given_date=None):
    if given_date is None:
        given_date = date.today()
        monday=None

    if given_date.weekday() == 0:
        print(f"Today is Monday: {given_date}")
        monday=True
    else:
        print(f"Today is not Monday: {given_date}")
        monday=False
    return monday, given_date


specific_date = date(2024, 10, 7)

def main():
    monday, given_date=check_day(specific_date)
    if monday:
        initialize_mt5()
        print(f"its Monday {given_date}")
        friday=get_last_friday()
        print(friday)
        for sym in symbols:
            symbol_data = sym['symbol']
            ticks = mt5.copy_ticks_range(symbol_data, 23, 59, mt5.COPY_TICKS_ALL)
            print(ticks)
    else:
        initialize_mt5()
        print(f"its not monday {given_date}")


main()




import MetaTrader5 as mt5
from datetime import datetime, timedelta
import pytz
import os
import json


current_dir = os.path.dirname(os.path.abspath(__file__))

# Create the full path to details.json
details_path = os.path.join(current_dir, 'details.json')

# Load details from details.json
with open(details_path) as f:
    config = json.load(f)

ist_timezone_fetch = pytz.timezone(config['timezone'])
broker_timezone_fetch = pytz.timezone('EET')  # Eastern European Time (EET)



def get_start_price_for_symbol(symbol, broker_timezone, ist_timezone):
    now_ist = datetime.now(ist_timezone)
    today_weekday = now_ist.weekday()  # Monday=0, ..., Sunday=6

    if today_weekday == 0:  # Monday
        # Fetch Friday's closing price
        last_friday_ist = now_ist - timedelta(days=3)  # Monday - 3 days = Friday
        last_friday_utc = last_friday_ist.astimezone(pytz.utc)
        friday_close_utc = pytz.utc.localize(datetime(
            last_friday_utc.year, last_friday_utc.month, last_friday_utc.day, 21, 0,
            0))  # Assuming 21:00 is market close
        friday_close_broker = friday_close_utc.astimezone(broker_timezone)

        # Get the last available price for Friday close
        closing_price, actual_time = get_last_available_price(symbol, friday_close_broker, broker_timezone,
                                                              price_type='close')

        if closing_price is not None:
            return {
                'symbol': symbol,
                'date': last_friday_ist.strftime('%Y-%m-%d'),
                'start_price': closing_price,
                'time': actual_time
            }
        else:
            print(f"Could not get Friday's closing price for {symbol}")
            return None

    else:
        # Fetch today's 1 AM IST price
        one_am_ist = ist_timezone.localize(datetime(
            now_ist.year, now_ist.month, now_ist.day, 1, 0, 0))  # 1 AM IST
        one_am_broker = one_am_ist.astimezone(broker_timezone)

        # Get the last available price for 1 AM IST
        start_price, actual_time = get_last_available_price(symbol, one_am_broker, broker_timezone, price_type='open')

        if start_price is not None:
            return {
                'symbol': symbol,
                'date': one_am_ist.strftime('%Y-%m-%d'),
                'start_price': start_price,
                'time': actual_time
            }
        else:
            print(f"No data available for {symbol} at 1 AM IST")
            return None


def get_last_available_price(symbol, desired_time_broker, broker_timezone, price_type='close'):
    """
    Fetches the last available price at or before the desired time.
    """
    max_attempts = 120  # Increased attempts to cover possible delays
    attempts = 0
    while attempts < max_attempts:
        rates = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M1, desired_time_broker, 1)
        if rates is not None and len(rates) > 0:
            price = rates[0][price_type]
            rate_time = datetime.fromtimestamp(rates[0]['time'], pytz.utc)
            return price, rate_time
        else:
            # Decrement time by 1 minute
            desired_time_broker -= timedelta(minutes=1)
            attempts += 1
            if attempts % 10 == 0:
                print(f"Attempt {attempts}: Could not find {price_type} price for {symbol}, retrying...")

    print(f"Failed to fetch {price_type} price for {symbol} after {max_attempts} attempts.")
    return None, None




get_start_price_for_symbol("EURUSD",broker_timezone_fetch, ist_timezone_fetch )

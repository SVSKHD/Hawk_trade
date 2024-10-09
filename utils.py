import MetaTrader5 as mt5
from datetime import datetime, timedelta
import pytz
from datetime import date, timedelta, datetime





def initialize_mt5():
    if not mt5.initialize():
        print("Failed to initialize MetaTrader 5")
        quit()


def get_start_price_for_symbol(symbol, broker_timezone, ist_timezone):
    now_ist = datetime.now(ist_timezone)
    today_weekday = now_ist.weekday()  # Monday=0, ..., Sunday=6

    if today_weekday == 0:  # Monday
        # Fetch Friday's closing price
        last_friday_ist = now_ist - timedelta(days=3)  # Monday - 3 days = Friday
        last_friday_utc = last_friday_ist.astimezone(pytz.utc)
        friday_close_utc = pytz.utc.localize(datetime(
            last_friday_utc.year, last_friday_utc.month, last_friday_utc.day, 23, 0,
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




def get_tick_values(symbol):
    # Get the tick information for the symbol
    tick_info = mt5.symbol_info_tick(symbol)
    if tick_info is None:
        raise ValueError(f"Failed to get tick info for {symbol}. Ensure the symbol is correct and active.")

    # Print and return the relevant tick data
    tick_data = {
        "symbol": symbol,
        "bid": tick_info.bid,
        "ask": tick_info.ask,
        "last": tick_info.last,
        "time": tick_info.time
    }

    print(f"Tick data for {symbol}: {tick_data}")
    return tick_data



def get_last_friday(given_date=None):
    # If no date is provided, use today's date
    if given_date is None:
        given_date = date.today()

    # Find how many days to subtract to reach last Friday
    days_ago = (given_date.weekday() + 2) % 7 + 1  # Monday = 0, Friday = 4
    last_friday = given_date - timedelta(days=days_ago)

    return last_friday


def check_day(given_date=None):
    # If no date is provided, use today's date
    if given_date is None:
        given_date = date.today()

    # Check if it's Monday (Monday is represented as 0)
    if given_date.weekday() == 0:
        print(f"Today is Monday: {given_date}")
        print(get_last_friday())
    else:
        print(f"Today is not Monday: {given_date}")



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
        return closing_price
    else:
        return None, "No data found"


def get_previous_day_full_date():
    # Get the current date and time
    now = datetime.now()

    # Calculate the previous day
    previous_day = now - timedelta(days=1)

    # Get the start of the previous day at 00:00:00
    start_of_previous_day = datetime.combine(previous_day.date(), datetime.min.time())

    # Get the end of the previous day at 23:59:59
    end_of_previous_day = datetime.combine(previous_day.date(), datetime.max.time().replace(second=59))

    return start_of_previous_day, end_of_previous_day

def get_date_wise_closing(symbol, date):

    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M5, date,date)
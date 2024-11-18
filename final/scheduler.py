import asyncio
from datetime import datetime, timedelta
import pytz
import MetaTrader5 as mt5
from scheduler_logic import calculate_pip_difference, calculate_thresholds, check_thresholds
from config import symbols_config
from scheduler_utils import fetch_start_and_current_price, log_error_and_notify, format_message, get_open_positions_scheduler
from notifications import send_discord_message_async  # Ensure this function is asynchronous


async def scheduled_task():
    """Task that fetches prices and sends messages at scheduled times."""
    timezone = pytz.timezone('Asia/Kolkata')
    now = datetime.now(timezone)
    print(f"Running scheduled task at {now.strftime('%Y-%m-%d %H:%M:%S')}")

    tasks = []
    for symbol in symbols_config:
        tasks.append(fetch_start_and_current_price(symbol))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for symbol, prices in zip(symbols_config, results):
        symbol_name = symbol["symbol"]
        if isinstance(prices, Exception):
            await log_error_and_notify(f"Exception occurred for {symbol_name}: {prices}")
            continue
        if prices:
            start_price = prices['start_price']
            current_price = prices['current_price']

            # Calculate pip difference
            pip_difference = await calculate_pip_difference(start_price, current_price)
            adjusted_pip_difference = pip_difference / symbol["pip_size"]

            # Calculate thresholds
            thresholds = await calculate_thresholds(symbol, adjusted_pip_difference)

            # Process symbol for trade checks
            threshold_data = await process_symbol(symbol, start_price, current_price)
            open_positions = await get_open_positions_scheduler(symbol)

            # Prepare data for the message
            data = {
                "symbol": symbol_name,
                "start_price": start_price,
                "current_price": current_price,
                "pip_difference": adjusted_pip_difference,
                "threshold": threshold_data['thresholds'],
                "direction": threshold_data['direction'],
                "trade_open": open_positions["no_of_positions"],  # Ensure this is an integer count
                "pips_to_positive_threshold": symbol.get('positive_pip_difference', None),
                "pips_to_negative_threshold": symbol.get('negative_pip_difference', None)
            }

            # Format and send message
            message = await format_message("hourly_update", data)
            await send_discord_message_async(message)
        else:
            await log_error_and_notify(f"Failed to fetch prices for {symbol_name}")


async def process_symbol(symbol, start_price, current_price):
    pip_difference = await calculate_pip_difference(start_price, current_price)
    adjusted_pip_difference = pip_difference / symbol["pip_size"]

    # Check thresholds
    threshold_data = await check_thresholds(symbol, adjusted_pip_difference)

    return threshold_data

async def scheduler():
    scheduled_times = [
        '09:00', '09:30', '10:00', '10:30', '11:00', '11:30', '12:00', '12:30',
        '13:00', '13:30', '14:00', '14:30', '15:00', '15:30', '16:00', '16:30',
        '17:00', '17:30', '18:00', '18:30', '19:00', '19:30', '20:00', '20:30',
        '21:00', '21:30', '22:00', '22:30', '23:00', '23:30'
    ]

    timezone = pytz.timezone('Asia/Kolkata')

    while True:
        now = datetime.now(timezone)
        today = now.date()
        scheduled_datetimes = [
            timezone.localize(datetime.combine(today, datetime.strptime(t, '%H:%M').time()))
            for t in scheduled_times
        ]

        next_run_time = None
        for scheduled_time in scheduled_datetimes:
            if scheduled_time > now:
                next_run_time = scheduled_time
                break

        if not next_run_time:
            next_day = now + timedelta(days=1)
            next_run_time = timezone.localize(
                datetime.combine(next_day.date(), datetime.strptime(scheduled_times[0], '%H:%M').time())
            )

        sleep_duration = (next_run_time - now).total_seconds()
        print(f"Sleeping for {sleep_duration} seconds until next scheduled task at {next_run_time.strftime('%Y-%m-%d %H:%M:%S')}")
        await asyncio.sleep(sleep_duration)
        await scheduled_task()

async def scheduler_main():
    if not mt5.initialize():
        await log_error_and_notify("Failed to initialize MT5")
        return
    print("MT5 initialized successfully.")

    try:
        await scheduler()
    finally:
        mt5.shutdown()
        print("MT5 shutdown.")

# To run
if __name__ == "__main__":
    asyncio.run(scheduler_main())

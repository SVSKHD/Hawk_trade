import asyncio
from utils import fetch_start_price, fetch_current_price, format_message
from datetime import datetime
from notifications import send_discord_message_async

async def send_hourly_update(symbol):
    start_price = await fetch_start_price(symbol)
    current_price = await fetch_current_price(symbol)

    if start_price is not None and current_price is not None:
        pip_difference = round((current_price - start_price) / 0.0001, 3)
        direction = "Upper" if pip_difference > 0 else "Down" if pip_difference < 0 else "Neutral"

        update_data = {
            "symbol": symbol,
            "start_price": start_price,
            "current_price": current_price,
            "pip_difference": pip_difference,
            "direction": direction,
            "pips_to_positive_threshold": 10 - pip_difference if pip_difference < 10 else 0,
            "pips_to_negative_threshold": 10 + pip_difference if pip_difference > -10 else 0,
        }

        # Format the message and send it
        message = await format_message("hourly_update", update_data)
        await send_discord_message_async(message)
    else:
        print(f"Failed to fetch prices for {symbol}")


async def scheduler(symbols):
    while True:
        current_time = datetime.now()
        wait_time = 60 - (current_time.minute * 60 + current_time.second)  # Wait until the next hour
        print(f"Waiting for {wait_time} seconds until the next hourly update...")

        await asyncio.sleep(wait_time)  # Wait until the next hour

        # Run updates concurrently for all symbols
        tasks = [send_hourly_update(symbol) for symbol in symbols]
        await asyncio.gather(*tasks)


async def start_scheduler(symbols):
    print("Starting the hourly update scheduler...")
    await scheduler(symbols)

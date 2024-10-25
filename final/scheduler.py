import asyncio
from config import symbols_config
from utils import fetch_and_print_price, format_message
from notifications import send_discord_message_async

async def send_hourly_update():
    """Send hourly updates for all symbols."""
    while True:
        await asyncio.sleep(3600)  # Wait for one hour
        tasks = [fetch_and_print_price(symbol) for symbol in symbols_config]
        results = await asyncio.gather(*tasks)
        for result in results:
            if result:
                formatted_message = format_message("hourly_update", result)
                await send_discord_message_async(formatted_message)

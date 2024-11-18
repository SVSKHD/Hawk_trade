import aiohttp
import datetime
import logging
from datetime import datetime
last_message_time = {}

# Define the interval between messages in seconds
MESSAGE_INTERVAL = 60  # Example: 60 seconds

async def send_discord_message_async(message):
    webhook_url = "https://discord.com/api/webhooks/1286192684834488350/gmXLG-RJT7WdiVNcT5Jw610lstwHRrU-lMmEgcBmQ538HlJp7ya1UyY7MJ46n5OAlIrk"
    data = {"content": message}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(webhook_url, json=data) as response:
                if response.status == 204:
                    print("Message sent successfully!")
                else:
                    print(f"Failed to send message: {response.status}, {await response.text()}")
        except Exception as e:
            print(f"Error sending message: {e}")

async def send_limited_message(symbol, message):
    current_time = datetime.now()
    last_time = last_message_time.get(symbol)
    if last_time is None or (current_time - last_time).total_seconds() > MESSAGE_INTERVAL:
        # Send the message and update the last message time
        logging.info(f"Sending message for {symbol}: {message}")
        await send_discord_message_async(message)
        last_message_time[symbol] = current_time  # Update last sent time
    else:
        # Skip sending the message to respect the rate limit
        logging.info(f"Message for {symbol} rate-limited; not sent.")
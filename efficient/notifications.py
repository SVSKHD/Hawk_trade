import aiohttp

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

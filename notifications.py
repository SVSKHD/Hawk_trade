import requests

def send_discord_message(message):
    webhook_url = "https://discord.com/api/webhooks/1286192684834488350/gmXLG-RJT7WdiVNcT5Jw610lstwHRrU-lMmEgcBmQ538HlJp7ya1UyY7MJ46n5OAlIrk"
    data = {"content": message}
    response = requests.post(webhook_url, json=data)
    if response.status_code == 204:
        print("Message sent successfully!")
    else:
        print(f"Failed to send message: {response.status_code}, {response.text}")
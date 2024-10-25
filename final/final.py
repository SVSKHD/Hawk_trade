import asyncio
from config import symbols_config, start_prices
from price_fetcher import initialize_start_prices, fetch_prices_batch
from notifications import send_discord_message_async
from scheduler import send_hourly_update
from utils import fetch_and_print_price, connect_mt5, fetch_start_price, fetch_current_price


async def main():
    """Main asynchronous function to process all symbols."""
    if not connect_mt5():
        print("Failed to connect to MetaTrader 5")
        return

    await initialize_start_prices()

    # Run hourly updates concurrently with price fetching
    asyncio.create_task(send_hourly_update())

    while True:
        symbols = [symbol["symbol"] for symbol in symbols_config]
        prices = await fetch_prices_batch(symbols)

        if prices:
            tasks = []
            for symbol in symbols_config:
                symbol_name = symbol["symbol"]
                if symbol_name in prices:
                    symbol_data = {
                        "symbol": symbol_name,
                        "current_price": prices[symbol_name],
                        "start_price": start_prices.get(symbol_name)
                    }
                    tasks.append(fetch_and_print_price(symbol_data))

            # Process all symbols concurrently
            await asyncio.gather(*tasks)

        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())

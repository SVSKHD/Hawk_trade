import asyncio
from fetch_prices import PriceFetcher
from logic import ThresholdTradingStrategy
from config import symbols_config
from utils import connect_mt5
from scheduler import scheduler_main


async def connect():
    """Connects to MetaTrader5 and returns connection status."""
    return await connect_mt5()


async def main():
    # Step 1: Establish connection to MT5
    connect_status = await connect()
    if not connect_status:
        print("Failed to connect to MetaTrader5.")
        return
    print("Connected to MetaTrader5.")

    # Step 2: Initialize PriceFetcher with symbols configuration
    price_fetcher = PriceFetcher(symbols_config)

    # Step 3: Fetch and continuously update prices for each symbol
    prices = await price_fetcher.fetch_all_current_prices()

    # Step 4: Initialize and start monitoring for each symbol
    tasks = []
    for symbol in symbols_config:
        start_price = prices[symbol["symbol"]]["start_price"]

        # Initialize the trading strategy for this symbol
        strategy = ThresholdTradingStrategy(symbol)

        # Start monitoring price changes using shared price data
        task = asyncio.create_task(
            strategy.monitor_price_changes(start_price, prices)
        )
        tasks.append(task)

    # Step 5: Update current prices periodically
    async def update_prices():
        while True:
            new_prices = await price_fetcher.fetch_all_current_prices()
            prices.update(new_prices)  # Update the shared dictionary
            await asyncio.sleep(1)  # Adjust frequency as needed

    # Step 6: Run all tasks concurrently
    await asyncio.gather(*tasks, update_prices())


async def combined_main():
    """Run scheduler_main and main concurrently."""
    await asyncio.gather(scheduler_main(), main())


# Run the combined main function
asyncio.run(combined_main())

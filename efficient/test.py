import asyncio
from scheduler import start_scheduler
from config import symbols_config
from utils import connect_mt5, fetch_start_price, fetch_current_price, check_thresholds_and_place_trades

# Global dictionaries to store prices for each symbol
start_prices = {}
current_prices = {}

async def run_schedulers(symbols_config):
    """Update start and current prices for each symbol."""
    for symbol in symbols_config:
        symbol_name = symbol["symbol"]

        # Fetch and update start and current prices in global dictionaries
        start_prices[symbol_name] = await fetch_start_price(symbol)
        current_prices[symbol_name] = await fetch_current_price(symbol)

        # Log failure if prices couldn't be fetched
        if start_prices[symbol_name] is None or current_prices[symbol_name] is None:
            print(f"Failed to fetch prices for {symbol_name}")

async def run_bot():
    """Check thresholds and place trades using the latest prices from global dictionaries."""
    for symbol in symbols_config:
        symbol_name = symbol["symbol"]
        start_price = start_prices.get(symbol_name)
        current_price = current_prices.get(symbol_name)

        # Ensure both start and current prices are available
        if start_price is not None and current_price is not None:
            await check_thresholds_and_place_trades(symbol, start_price, current_price)
        else:
            print(f"Skipping threshold check for {symbol_name} due to missing price data")

async def periodic_task(interval, symbols_config):
    """Periodically update prices and run trading bot tasks."""
    while True:
        await run_schedulers(symbols_config)  # Update prices
        await run_bot()  # Run trading bot actions based on updated prices
        await asyncio.sleep(interval)

if __name__ == "__main__":
    try:
        if asyncio.run(connect_mt5()):
            print("Connected to MetaTrader 5.")
            asyncio.run(periodic_task(1, symbols_config))  # Run every 1 second
        else:
            print("Failed to connect to MetaTrader 5.")
    except KeyboardInterrupt:
        print("Scheduler stopped manually.")

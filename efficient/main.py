import asyncio
from scheduler import start_scheduler
from config import symbols_config
from utils import connect_mt5

async def run_schedulers(symbols_config):
    """Run the scheduler for each symbol in the config."""
    # Extract symbols from config
    symbols = [config["symbol"] for config in symbols_config]
    # Start the scheduler for the symbols concurrently
    await start_scheduler(symbols)

if __name__ == "__main__":
    try:
        # Check MT5 connection asynchronously
        if asyncio.run(connect_mt5()):
            # Run the schedulers for all symbols
            asyncio.run(run_schedulers(symbols_config))
        else:
            print("Failed to connect to MetaTrader 5.")
    except KeyboardInterrupt:
        print("Scheduler stopped manually.")

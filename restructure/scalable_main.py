# main.py
from connect import connect_mt5
from scheduler import scheduler_main
from scalable_price_details import PriceFetcher
import asyncio
from config import symbols_config

async def main():
    result = await connect_mt5()
    if result:
        fetcher = PriceFetcher(symbols_config)  # Initialize PriceFetcher

        try:
            # Run scheduler_main and fetcher.monitor_prices concurrently
            await asyncio.gather(
                scheduler_main(),           # Runs the scheduler
                fetcher.monitor_prices()    # Continuously monitors prices
            )
        finally:
            print ("will diconnect") # Ensure the connection is closed after the tasks
    else:
        print("Failed to connect to MetaTrader5.")

if __name__ == '__main__':
    asyncio.run(main())

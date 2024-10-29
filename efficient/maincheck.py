import asyncio
from scheduler import start_scheduler
from config import symbols_config
from utils import connect_mt5, fetch_start_price, fetch_current_price, check_thresholds_and_place_trades

async def run_schedulers(symbols_config):
    for symbol in symbols_config:
        symbol_name = symbol["symbol"]

        # Fetch start and current prices for the symbol
        start_price = await fetch_start_price(symbol)
        current_price = await fetch_current_price(symbol)

        if start_price is not None and current_price is not None:
            await check_thresholds_and_place_trades(symbol, start_price, current_price)
        else:
            print(f"Failed to fetch prices for {symbol_name}")
    await start_scheduler(symbols_config)

if __name__ == "__main__":
    try:
        if asyncio.run(connect_mt5()):
            print("Connected to MetaTrader 5.")
            asyncio.run(run_schedulers(symbols_config))
        else:
            print("Failed to connect to MetaTrader 5.")
    except KeyboardInterrupt:
        print("Scheduler stopped manually.")

import asyncio
import MetaTrader5 as mt5
from config import start_prices, symbols_config
from utils import fetch_start_price

async def fetch_with_retries(fetch_func, symbol, max_retries=3, delay=2):
    retries = 0
    while retries < max_retries:
        try:
            return await asyncio.to_thread(fetch_func, symbol)
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}. Retrying...")
            retries += 1
            await asyncio.sleep(delay * (2 ** retries))
    return None

async def fetch_prices_batch(symbols):
    """Fetch prices for multiple symbols in a batch."""
    try:
        return {symbol: await asyncio.to_thread(mt5.symbol_info_tick, symbol).bid for symbol in symbols}
    except Exception as e:
        print(f"Batch fetch error: {e}")
        return None

async def initialize_start_prices():
    """Fetch start prices for all symbols initially."""
    global start_prices
    tasks = [fetch_with_retries(fetch_start_price, symbol["symbol"]) for symbol in symbols_config]
    results = await asyncio.gather(*tasks)

    for symbol, start_price in zip(symbols_config, results):
        if start_price is not None:
            start_prices[symbol["symbol"]] = start_price
        else:
            print(f"Failed to fetch start price for {symbol['symbol']}")

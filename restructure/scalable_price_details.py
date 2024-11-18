# price_fetcher.py
import MetaTrader5 as mt5
import asyncio
import logging
from config import symbols_config

class PriceFetcher:
    def __init__(self, symbols_config):
        self.symbols_config = symbols_config
        self.start_prices = {}  # To store start prices for each symbol

    async def log_error_and_notify(self, message):
        logging.error(message)
        print(message)

    async def fetch_current_price(self, symbol):
        """Fetches the current price for a given symbol."""
        symbol_name = symbol["symbol"]
        selected = await asyncio.to_thread(mt5.symbol_select, symbol_name, True)
        if not selected:
            await self.log_error_and_notify(f"Failed to select symbol {symbol_name} for fetching current price.")
            return None

        tick = await asyncio.to_thread(mt5.symbol_info_tick, symbol_name)
        if tick:
            return tick.bid
        else:
            await self.log_error_and_notify(f"Failed to get current price for {symbol_name}")
            return None

    async def fetch_start_price(self, symbol):
        """Fetch the start price for the symbol (usually at the beginning of the day)."""
        symbol_name = symbol["symbol"]
        if symbol_name not in self.start_prices:
            self.start_prices[symbol_name] = await self.fetch_current_price(symbol)  # Initial start price
        return self.start_prices[symbol_name]

    async def fetch_all_current_prices(self):
        """Fetches current prices along with the start prices for each symbol."""
        result = {}
        for symbol in self.symbols_config:
            start_price = await self.fetch_start_price(symbol)
            current_price = await self.fetch_current_price(symbol)
            if current_price is not None:
                result[symbol["symbol"]] = {
                    "start_price": start_price,
                    "current_price": current_price
                }
        return result

    async def monitor_prices(self):
        """Continuously fetches the latest prices every second."""
        while True:
            prices = await self.fetch_all_current_prices()
            await asyncio.sleep(1)  # Wait 1 second before fetching again
            yield prices

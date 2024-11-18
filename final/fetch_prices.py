import MetaTrader5 as mt5
import asyncio
import logging
from datetime import datetime, timedelta
import pytz
from config import symbols_config

class PriceFetcher:
    def __init__(self, symbols_config):
        self.symbols_config = symbols_config
        self.start_prices = {}  # To store start prices for each symbol
        self.timezone = pytz.timezone('Asia/Kolkata')  # Set the timezone

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

    async def refresh_start_prices(self):
        """Refreshes start prices for all symbols at 12:00 AM each day."""
        current_day = datetime.now(self.timezone).date()

        for symbol in self.symbols_config:
            symbol_name = symbol["symbol"]
            start_of_day = datetime.now(self.timezone).replace(hour=0, minute=0, second=0, microsecond=0)
            start_of_day_utc = start_of_day.astimezone(pytz.utc)

            # Fetch the first available price after midnight
            rates = await asyncio.to_thread(mt5.copy_rates_from, symbol_name, mt5.TIMEFRAME_M5, start_of_day_utc, 1)
            if rates is not None and len(rates) > 0:
                start_price = rates[0]["close"]
                # Update start price in cache
                self.start_prices[symbol_name] = {"price": start_price, "date": current_day}
            else:
                await self.log_error_and_notify(f"Failed to get start price at 12:00 AM for {symbol_name}")

    async def get_start_price(self, symbol):
        """Retrieves the cached start price for the symbol, refreshing if needed."""
        symbol_name = symbol["symbol"]
        current_day = datetime.now(self.timezone).date()

        # Refresh start prices if they are not for today
        if symbol_name not in self.start_prices or self.start_prices[symbol_name]["date"] != current_day:
            await self.refresh_start_prices()

        return self.start_prices.get(symbol_name, {}).get("price")

    async def fetch_all_current_prices(self):
        """Fetches current prices along with the start prices for each symbol."""
        result = {}
        for symbol in self.symbols_config:
            start_price = await self.get_start_price(symbol)
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

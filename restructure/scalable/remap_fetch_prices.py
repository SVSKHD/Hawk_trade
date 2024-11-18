# price_fetcher.py

import MetaTrader5 as mt5
import asyncio
import logging
from datetime import datetime, timedelta
import pytz

class PriceFetcher:
    def __init__(self, symbols_config):
        """
        Initialize the PriceFetcher with a list of symbols.

        Parameters:
        - symbols_config (list): A list of dictionaries with symbol information.
        """
        self.symbols_config = symbols_config

    async def log_error_and_notify(self, message):
        """Logs an error message and sends a notification (placeholder)."""
        logging.error(message)
        # Placeholder for a notification function, e.g., Discord or email notification
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
            return tick.bid  # or tick.ask depending on your requirements
        else:
            await self.log_error_and_notify(f"Failed to get current price for {symbol_name}")
            return None

    async def fetch_friday_closing_price(self, symbol):
        """Fetch the last Friday's closing price for a symbol."""
        timezone = pytz.timezone('Asia/Kolkata')
        today = datetime.now(timezone)
        symbol_name = symbol["symbol"]
        days_since_friday = (today.weekday() - 4) % 7
        last_friday = today - timedelta(days=days_since_friday)
        last_friday = last_friday.replace(hour=23, minute=59, second=59, microsecond=0)
        utc_from = last_friday.astimezone(pytz.utc)

        rates = await asyncio.to_thread(mt5.copy_rates_from, symbol_name, mt5.TIMEFRAME_M5, utc_from, 1)
        if rates is not None and len(rates) > 0:
            closing_price = rates[0]['close']
            print(f"Fetched last Friday's closing price for {symbol_name}: {closing_price}")
            return closing_price

        await self.log_error_and_notify(f"Failed to get last Friday's closing price for {symbol_name}")
        return None

    async def fetch_price(self, symbol, price_type):
        """Fetches the price based on type: start or current."""
        symbol_name = symbol["symbol"]

        selected = await asyncio.to_thread(mt5.symbol_select, symbol_name, True)
        if not selected:
            await self.log_error_and_notify(f"Failed to select symbol {symbol_name} for fetching {price_type} price.")
            return None

        if price_type == "current":
            tick = await asyncio.to_thread(mt5.symbol_info_tick, symbol_name)
            if tick:
                return tick.bid  # or tick.ask depending on requirements

        elif price_type == "start":
            timezone = pytz.timezone('Asia/Kolkata')
            now = datetime.now(timezone)
            if now.weekday() == 0:  # Monday
                return await self.fetch_friday_closing_price(symbol)

            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            start_of_day_utc = start_of_day.astimezone(pytz.utc)
            rates = await asyncio.to_thread(mt5.copy_rates_from, symbol_name, mt5.TIMEFRAME_M5, start_of_day_utc, 1)
            if rates is not None and len(rates) > 0:
                return rates[0]["close"]

        await self.log_error_and_notify(f"Failed to get {price_type} price for {symbol_name}")
        return None

    async def fetch_start_and_current_price(self, symbol):
        """Fetch both start and current prices concurrently for a given symbol."""
        symbol_name = symbol["symbol"]
        print(f"Fetching prices for {symbol_name}")

        # Fetch start price and current price concurrently
        start_price_task = asyncio.create_task(self.fetch_price(symbol, "start"))
        current_price_task = asyncio.create_task(self.fetch_price(symbol, "current"))

        # Await the results
        start_price = await start_price_task
        current_price = await current_price_task

        # Check if both prices were fetched successfully
        if start_price is None or current_price is None:
            await self.log_error_and_notify(f"Failed to fetch prices for {symbol_name}")
            return None

        print(f"Fetched prices for {symbol_name}: Start Price = {start_price}, Current Price = {current_price}")
        return {"start_price": start_price, "current_price": current_price}

    async def fetch_all_current_prices(self):
        """
        Fetches the current prices for all symbols concurrently.

        Returns:
        - dict: A dictionary with symbols as keys and their current prices as values.
        """
        tasks = [self.fetch_current_price(symbol) for symbol in self.symbols_config]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return {symbol["symbol"]: price for symbol, price in zip(self.symbols_config, results)}

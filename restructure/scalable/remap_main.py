# remap_main.py

import MetaTrader5 as mt5
import asyncio
from remap_fetch_prices import PriceFetcher
from remap_trade_logic_generic import ThresholdTradingStrategy
from config import symbols_config


async def initialize_and_run_trading_strategy():
    if not mt5.initialize():
        print("Failed to initialize MetaTrader5.")
        return

    fetcher = PriceFetcher(symbols_config)

    strategies = []
    for symbol in symbols_config:
        prices = await fetcher.fetch_start_and_current_price(symbol)
        if prices:
            start_price = prices["start_price"]
            current_price = prices["current_price"]
            print(f"Symbol: {symbol['symbol']}, Start Price: {start_price}, Current Price: {current_price}")

            strategy = ThresholdTradingStrategy(symbol)
            strategies.append(strategy.monitor_price_changes(start_price, fetcher.fetch_current_price))
        else:
            print(f"Failed to fetch prices for {symbol['symbol']}")

    await asyncio.gather(*strategies)
    mt5.shutdown()


if __name__ == "__main__":
    asyncio.run(initialize_and_run_trading_strategy())

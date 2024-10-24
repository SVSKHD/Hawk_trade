import MetaTrader5 as mt5
import asyncio
import pytz
from notifications import send_discord_message
from utils import (
    fetch_start_price,
    fetch_current_price,
    connect_mt5,
    format_message,
    place_trade_notify,
    close_trades_by_symbol
)

# Symbols configuration
symbols_config = [
    {
        "symbol": "EURUSD",
        "positive_pip_difference": 15,
        "negative_pip_difference": -15,
        "positive_pip_range": 17,  # Buffer range for positive pips
        "negative_pip_range": -17,  # Buffer range for negative pips
        "close_trade_at": 10,
        "close_trade_at_opposite_direction": 8,
        "pip_size": 0.0001,
        "lot_size": 1.0
    },
    {
        "symbol": "GBPUSD",
        "positive_pip_difference": 15,
        "negative_pip_difference": -15,
        "positive_pip_range": 17,
        "negative_pip_range": -17,
        "close_trade_at": 10,
        "close_trade_at_opposite_direction": 8,
        "pip_size": 0.0001,
        "lot_size": 1.0
    }
]

# Initialize start prices for symbols
start_prices = {symbol["symbol"]: None for symbol in symbols_config}

async def fetch_and_print_price(symbol):
    """Fetch current price asynchronously and print it."""
    symbol_name = symbol["symbol"]
    pip_size = symbol["pip_size"]

    try:
        # Fetch current price asynchronously
        current_price = await asyncio.to_thread(fetch_current_price, symbol_name)

        if current_price is not None:
            print(f"Current price of {symbol_name}: {current_price}")
        else:
            print(f"Failed to fetch the price for {symbol_name}")

    except Exception as e:
        print(f"Error fetching price for {symbol_name}: {e}")

async def main():
    """Main asynchronous function to process all symbols."""
    # Connect to MetaTrader 5
    if not connect_mt5():
        print("Failed to connect to MetaTrader 5")
        return

    # Start fetching prices for all symbols concurrently
    tasks = [fetch_and_print_price(symbol) for symbol in symbols_config]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    # Run the main function using asyncio
    asyncio.run(main())

import asyncio
from utils import (
    connect_mt5,
    fetch_current_price,
    fetch_start_price,
    place_trade_notify,
    close_trades_by_symbol,
    fetch_and_print_price
)

async def main():
    # Test the connection to MetaTrader 5
    print("Testing MT5 connection...")
    connected = await connect_mt5()
    if connected:
        print("Connected to MT5 successfully.")
    else:
        print("Failed to connect to MT5.")
        return  # Stop further tests if connection fails

    # Test fetching the current price for a symbol
    symbol = {"symbol": "BTCUSD"}
    current_price = await fetch_current_price(symbol)
    print(f"Current price for {symbol['symbol']}: {current_price}")
    #
    # Test fetching the start price for the day for a symbol
    start_price = await fetch_start_price(symbol)
    print(f"Start price for {symbol['symbol']}: {start_price}")

# Run the main function to test
asyncio.run(main())

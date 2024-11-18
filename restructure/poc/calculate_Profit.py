import MetaTrader5 as mt5


def calculate_profit(symbol, lot, distance, account_currency="USD"):
    """
    Calculates the profit for buy and sell orders for a given symbol.

    Parameters:
    - symbol (str): The trading symbol, e.g., "EURUSD".
    - lot (float): The number of lots.
    - distance (int): The number of points for calculating potential profit.
    - account_currency (str): The account currency for displaying profit.

    Returns:
    - dict: A dictionary with buy and sell profit information.
    """
    # Check if symbol information is available and visible
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"{symbol} not found, skipped")
        return None

    # Ensure the symbol is visible in the Market Watch
    if not symbol_info.visible:
        print(f"{symbol} is not visible, trying to switch on")
        if not mt5.symbol_select(symbol, True):
            print(f"symbol_select({symbol}) failed, skipped")
            return None

    # Retrieve the tick data
    symbol_tick = mt5.symbol_info_tick(symbol)
    if symbol_tick is None:
        print(f"Failed to get tick data for {symbol}")
        return None

    # Extract necessary values
    point = symbol_info.point
    ask = symbol_tick.ask
    bid = symbol_tick.bid

    # Calculate potential buy profit
    buy_profit = mt5.order_calc_profit(mt5.ORDER_TYPE_BUY, symbol, lot, ask, ask + distance * point)
    if buy_profit is None:
        print(f"order_calc_profit(ORDER_TYPE_BUY) failed for {symbol}, error code =", mt5.last_error())
        buy_profit = "Calculation failed"

    # Calculate potential sell profit
    sell_profit = mt5.order_calc_profit(mt5.ORDER_TYPE_SELL, symbol, lot, bid, bid - distance * point)
    if sell_profit is None:
        print(f"order_calc_profit(ORDER_TYPE_SELL) failed for {symbol}, error code =", mt5.last_error())
        sell_profit = "Calculation failed"

    # Display the results
    print(f"Symbol: {symbol}")
    print(f"   Buy Profit: {buy_profit} {account_currency} on {distance} points")
    print(f"   Sell Profit: {sell_profit} {account_currency} on {distance} points\n")

    return {
        "symbol": symbol,
        "buy_profit": buy_profit,
        "sell_profit": sell_profit,
        "account_currency": account_currency
    }


# Example usage of the function
if __name__ == "__main__":
    # Initialize MetaTrader5
    if not mt5.initialize():
        print("Failed to initialize MetaTrader5.")
    else:
        symbols = ["EURUSD", "GBPUSD"]  # List of symbols
        lot = 0.1  # Define the lot size
        distance = 50  # Define the distance in points for profit calculation

        # Calculate and display profit for each symbol
        for symbol in symbols:
            calculate_profit(symbol, lot, distance)

        # Shut down connection to MetaTrader 5
        mt5.shutdown()

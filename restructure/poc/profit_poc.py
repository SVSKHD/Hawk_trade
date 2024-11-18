import MetaTrader5 as mt5


def calculate_profit_distance(symbol, lot, distance, account_currency="USD"):
    """
    Calculates the profit for buy and sell orders for a given symbol based on a distance in points.

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
    print(f"   Buy Profit (distance {distance} points): {buy_profit} {account_currency}")
    print(f"   Sell Profit (distance {distance} points): {sell_profit} {account_currency}\n")

    return {
        "symbol": symbol,
        "buy_profit": buy_profit,
        "sell_profit": sell_profit,
        "account_currency": account_currency
    }


def calculate_profit_prices(symbol, lot, entry_price, exit_price, order_type, account_currency="USD"):
    """
    Calculates the profit for an order based on entry and exit prices for a given symbol.

    Parameters:
    - symbol (str): The trading symbol, e.g., "EURUSD".
    - lot (float): The number of lots.
    - entry_price (float): The price at which the position was opened.
    - exit_price (float): The price at which the position is planned to close.
    - order_type (str): Either "buy" or "sell", indicating the type of trade.
    - account_currency (str): The account currency for displaying profit.

    Returns:
    - float or str: The calculated profit if successful, or an error message.
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

    # Determine the MetaTrader5 order type
    mt5_order_type = mt5.ORDER_TYPE_BUY if order_type.lower() == "buy" else mt5.ORDER_TYPE_SELL

    # Calculate profit based on entry and exit prices
    profit = mt5.order_calc_profit(mt5_order_type, symbol, lot, entry_price, exit_price)

    if profit is None:
        print(f"order_calc_profit({order_type.upper()}) failed for {symbol}, error code =", mt5.last_error())
        return "Calculation failed"

    # Display the results
    print(f"Symbol: {symbol}")
    print(
        f"   {order_type.capitalize()} Profit: {profit} {account_currency} (Entry: {entry_price}, Exit: {exit_price})\n")

    return profit


# Example usage of the functions
if __name__ == "__main__":
    # Initialize MetaTrader5
    if not mt5.initialize():
        print("Failed to initialize MetaTrader5.")
    else:
        symbols = ["EURUSD", "GBPUSD"]  # List of symbols
        lot = 0.1  # Define the lot size
        distance = 50  # Define the distance in points for profit calculation

        # Calculate and display profit using distance for each symbol
        print("Calculating profit using distance:")
        for symbol in symbols:
            calculate_profit_distance(symbol, lot, distance)

        # Calculate and display profit using entry and exit prices
        print("\nCalculating profit using entry and exit prices:")
        # Define parameters for the profit calculation
        account_currency = "USD"

        entry_price_eurusd = 1.1000  # Example entry price for EURUSD
        exit_price_eurusd = 1.1050  # Example exit price for EURUSD
        order_type_eurusd = "buy"  # Type of order, either "buy" or "sell"

        entry_price_gbpusd = 1.3000  # Example entry price for GBPUSD
        exit_price_gbpusd = 1.2950  # Example exit price for GBPUSD
        order_type_gbpusd = "sell"  # Type of order, either "buy" or "sell"

        # Calculate and display profit for EURUSD
        profit_eurusd = calculate_profit_prices("EURUSD", lot, entry_price_eurusd, exit_price_eurusd, order_type_eurusd,
                                                account_currency)

        # Calculate and display profit for GBPUSD
        profit_gbpusd = calculate_profit_prices("GBPUSD", lot, entry_price_gbpusd, exit_price_gbpusd, order_type_gbpusd,
                                                account_currency)

        # Shut down connection to MetaTrader 5
        mt5.shutdown()

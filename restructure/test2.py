import asyncio


eurusd = {
    "symbol": "EURUSD",
    "positive_pip_difference": 15,
    "negative_pip_difference": -15,
    "positive_pip_range": 17,
    "negative_pip_range": -17,
    "close_trade_at": 10,
    "close_trade_at_opposite_direction": 8,
    "pip_size": 0.0001,
    "lot_size": 1.0
}

# Combined list of prices to test both buy and sell cases
combined_prices = [
    # Buy case prices (increasing to 1 threshold, then reversing to below 0.5)
    1.096799, 1.097299, 1.097799, 1.098299, 1.098799,
    1.099299, 1.099799, 1.100299, 1.100799, 1.101299,  # Reaches the 1 threshold
    1.100799, 1.100299, 1.099799, 1.099299, 1.098799,  # Reverses

    # Sell case prices (decreasing to -1 threshold, then reversing to above -0.5)
    1.096799, 1.096299, 1.095799, 1.095299, 1.094799,
    1.094299, 1.093799, 1.093299, 1.092799, 1.092299,  # Reaches the -1 threshold
    1.092799, 1.093299, 1.093799, 1.094299, 1.094799  # Reverses
]

start_price = 1.096799  # Define the starting price for comparison


async def calculate_pip_difference(current_price, start_price):
    """Calculate the pip difference between the current and start price."""
    return current_price - start_price


async def test_calculate_pip_difference(symbol, current_price, start_price):
    """Calculate adjusted pip difference for a given symbol."""
    pip_difference = await calculate_pip_difference(current_price, start_price)
    result = pip_difference / symbol['pip_size']
    return result


async def check_thresholds(symbol, current_price, start_price):
    """Calculate the number of thresholds based on pip difference."""
    pip_difference = await test_calculate_pip_difference(symbol, current_price, start_price)
    no_of_thresholds = pip_difference / symbol["positive_pip_difference"]
    data = {
        "symbol": symbol["symbol"],
        "thresholds": no_of_thresholds,
        "pip_difference": pip_difference
    }
    return data


async def place_hedging_trade(symbol, direction, price):
    """Placeholder function to simulate placing an opposite trade for hedging."""
    opposite_direction = "sell" if direction == "buy" else "buy"
    print(f"Hedging initiated: Placing {opposite_direction} trade at {price} due to reversal.")
    return price  # Returning the price at which hedging is initiated


async def close_trade(symbol, direction, price):
    """Placeholder function to simulate closing a trade."""
    print(f"Closing {direction} trade at {price} as opposite 1 threshold is reached.")


async def trigger_trade_by_threshold(symbol, current_price, start_price, trade_placed, initial_direction,
                                     hedging_entry_price):
    """Trigger trades based on threshold conditions and handle hedging and closing if needed."""
    threshold_data = await check_thresholds(symbol, current_price, start_price)
    no_of_thresholds = round(threshold_data["thresholds"], 2)
    pip_difference = round(threshold_data["pip_difference"], 4)

    print(f"Current Price: {current_price}, Pip Difference: {pip_difference}, Thresholds: {no_of_thresholds}")

    # Place the initial trade at the 1 or -1 threshold
    if not trade_placed and abs(no_of_thresholds) >= 1:
        direction = "buy" if no_of_thresholds > 0 else "sell"
        print(
            f"{direction.capitalize()} Threshold reached at {current_price}, placing initial trade. Thresholds: {no_of_thresholds}")
        trade_placed = True
        initial_direction = direction

    # Check for reversal and trigger hedging if it moves below or equal to 0.5 threshold after the trade
    elif trade_placed and abs(no_of_thresholds) <= 0.5 and hedging_entry_price is None:
        print(f"Reversal detected at {current_price} with Thresholds: {no_of_thresholds}.")
        hedging_entry_price = await place_hedging_trade(symbol, initial_direction, current_price)

    # Check if we reach the opposite 1 threshold from the hedging entry price to close the trade
    elif hedging_entry_price is not None:
        opposite_threshold = abs((current_price - hedging_entry_price) / symbol['pip_size']) / symbol[
            "positive_pip_difference"]

        if opposite_threshold >= 1:
            close_direction = "sell" if initial_direction == "buy" else "buy"
            await close_trade(symbol, close_direction, current_price)
            trade_placed = False  # Reset the trade status after closing
            hedging_entry_price = None  # Reset hedging entry price

    return trade_placed, initial_direction, hedging_entry_price


async def main():
    trade_placed = False  # Track if the initial trade has been placed
    initial_direction = None  # Track the initial trade direction ("buy" or "sell")
    hedging_entry_price = None  # Track the price at which hedging is initiated

    for current_price in combined_prices:
        trade_placed, initial_direction, hedging_entry_price = await trigger_trade_by_threshold(
            eurusd, current_price, start_price, trade_placed, initial_direction, hedging_entry_price
        )
        print("---")  # Separator for readability


# Run the main function
asyncio.run(main())

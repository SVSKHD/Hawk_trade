import asyncio


class ThresholdTradingStrategy:
    def __init__(self, symbol_config, start_price):
        self.symbol_config = symbol_config
        self.start_price = start_price
        self.trade_placed = False
        self.initial_direction = None
        self.hedging_entry_price = None

    async def calculate_pip_difference(self, current_price):
        """Calculate the pip difference between the current and start price."""
        return current_price - self.start_price

    async def check_thresholds(self, current_price):
        """Calculate the number of thresholds based on pip difference."""
        pip_difference = await self.calculate_pip_difference(current_price)
        no_of_thresholds = pip_difference / self.symbol_config["positive_pip_difference"]
        return {
            "symbol": self.symbol_config["symbol"],
            "thresholds": no_of_thresholds,
            "pip_difference": pip_difference
        }

    async def place_initial_trade(self, direction, price):
        """Simulate placing the initial trade at the 1 threshold."""
        print(f"Placing initial {direction} trade at {price}.")
        self.trade_placed = True
        self.initial_direction = direction

    async def place_hedging_trades(self, price):
        """Simulate placing two opposite hedging trades."""
        opposite_direction = "sell" if self.initial_direction == "buy" else "buy"
        print(f"Hedging initiated: Placing two {opposite_direction} trades at {price}.")
        self.hedging_entry_price = price  # Track hedging entry price

    async def close_trade(self, direction, price, reason):
        """Simulate closing a trade."""
        print(f"Closing {direction} trade at {price}. Reason: {reason}")
        self.trade_placed = False  # Reset after closing
        self.hedging_entry_price = None  # Reset hedging entry price

    async def trigger_trade_by_threshold(self, current_price):
        """Core trading logic for threshold detection, hedging, and closure."""
        threshold_data = await self.check_thresholds(current_price)
        no_of_thresholds = round(threshold_data["thresholds"], 2)
        pip_difference = round(threshold_data["pip_difference"], 4)

        print(f"Current Price: {current_price}, Pip Difference: {pip_difference}, Thresholds: {no_of_thresholds}")

        # Step 1: Place the initial trade at the 1 or -1 threshold
        if not self.trade_placed and abs(no_of_thresholds) >= 1:
            direction = "buy" if no_of_thresholds > 0 else "sell"
            await self.place_initial_trade(direction, current_price)

        # Step 2: Trigger hedging if price reverses to or below the 0.5 threshold after initial trade
        elif self.trade_placed and abs(no_of_thresholds) <= 0.5 and self.hedging_entry_price is None:
            print(f"Reversal detected at {current_price} with Thresholds: {no_of_thresholds}.")
            await self.place_hedging_trades(current_price)

        # Step 3: Close trade if opposite 1 threshold is reached from the hedging entry
        elif self.hedging_entry_price is not None:
            opposite_threshold = abs((current_price - self.hedging_entry_price) / self.symbol_config['pip_size']) / \
                                 self.symbol_config["positive_pip_difference"]

            if opposite_threshold >= 1:
                close_direction = "sell" if self.initial_direction == "buy" else "buy"
                await self.close_trade(close_direction, current_price, "Opposite 1 threshold reached after hedging")


async def main():
    eurusd_config = {
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

    # Starting price for calculations
    start_price = 1.096799

    # Instantiate the trading strategy with configuration and start price
    strategy = ThresholdTradingStrategy(eurusd_config, start_price)

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

    # Process each price in the combined list
    for current_price in combined_prices:
        await strategy.trigger_trade_by_threshold(current_price)
        print("---")  # Separator for readability


# Run the main function
asyncio.run(main())

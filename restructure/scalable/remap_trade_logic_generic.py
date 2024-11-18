# threshold_trading_strategy.py

import asyncio


class ThresholdTradingStrategy:
    def __init__(self, symbol_config):
        self.symbol_config = symbol_config
        self.trade_placed = False
        self.initial_direction = None
        self.hedging_entry_price = None
        self.hedging_prices = []  # Track prices where hedging is initiated

    async def calculate_pip_difference(self, start_price, current_price):
        """Calculate the pip difference between the current and start price."""
        return current_price - start_price

    async def check_thresholds(self, start_price, current_price):
        """Calculate the number of thresholds based on pip difference."""
        pip_difference = await self.calculate_pip_difference(start_price, current_price)
        formatted_pip_difference = pip_difference / self.symbol_config["pip_size"]
        no_of_thresholds = formatted_pip_difference / self.symbol_config["positive_pip_difference"]
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
        """Simulate placing two opposite hedging trades and log the hedging price."""
        opposite_direction = "sell" if self.initial_direction == "buy" else "buy"
        print(f"Hedging initiated: Placing two {opposite_direction} trades at {price}.")
        self.hedging_entry_price = price  # Track hedging entry price
        self.hedging_prices.append(price)  # Log the price at which hedging is initiated

    async def close_trade(self, direction, price, reason):
        """Simulate closing a trade."""
        print(f"Closing {direction} trade at {price}. Reason: {reason}")
        self.trade_placed = False  # Reset after closing
        self.hedging_entry_price = None  # Reset hedging entry price

    async def trigger_trade_by_threshold(self, start_price, current_price):
        """Core trading logic for threshold detection, hedging, and closure."""
        threshold_data = await self.check_thresholds(start_price, current_price)
        no_of_thresholds = round(threshold_data["thresholds"], 2)
        pip_difference = round(threshold_data["pip_difference"], 4)

        print(f"Symbol: {self.symbol_config['symbol']}, Start Price: {start_price}, "
              f"Current Price: {current_price}, Pip Difference: {pip_difference}, "
              f"Thresholds: {no_of_thresholds}")

        # Step 1: Place the initial trade at the 1 or -1 threshold
        if not self.trade_placed and abs(no_of_thresholds) >= 1:
            direction = "buy" if no_of_thresholds > 0 else "sell"
            await self.place_initial_trade(direction, current_price)

        # Step 2: Trigger hedging if price reverses to or below the 0.5 threshold after initial trade
        elif self.trade_placed and abs(no_of_thresholds) <= 0.5 and self.hedging_entry_price is None:
            print(f"Reversal detected at {current_price} with Thresholds: {no_of_thresholds}. Initiating hedging.")
            await self.place_hedging_trades(current_price)

        # Step 3: Close trade if opposite 1 threshold is reached from the hedging entry
        elif self.hedging_entry_price is not None:
            opposite_threshold = abs((current_price - self.hedging_entry_price) / self.symbol_config['pip_size']) / \
                                 self.symbol_config["positive_pip_difference"]

            if opposite_threshold >= 1:
                close_direction = "sell" if self.initial_direction == "buy" else "buy"
                await self.close_trade(close_direction, current_price, "Opposite 1 threshold reached after hedging")

    async def monitor_price_changes(self, start_price, price_fetcher):
        """Monitor price changes using provided price fetcher."""
        while True:
            current_price = await price_fetcher(self.symbol_config["symbol"])
            await self.trigger_trade_by_threshold(start_price, current_price)
            await asyncio.sleep(1)  # Adjust frequency as needed

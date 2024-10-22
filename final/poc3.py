import MetaTrader5 as mt5
import pytz
from datetime import datetime, timedelta

from Hawk_trade.poc1 import fetch_start_prices
from utils import fetch_current_price, fetch_start_price, connect_mt5, format_message, place_trade_notify, close_trades_by_symbol
from notifications import send_discord_message
import time
import logging

# Configuration for symbols with buffer range
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
    },
    {
        "symbol": "USDJPY",
        "positive_pip_difference": 15,
        "negative_pip_difference": -15,
        "positive_pip_range": 17,
        "negative_pip_range": -17,
        "close_trade_at": 10,
        "close_trade_at_opposite_direction": 7,
        "pip_size": 0.01,
        "lot_size": 1.0
    }
]

# State tracking
last_sent_direction = {symbol["symbol"]: None for symbol in symbols_config}
last_hourly_check = time.time()
current_direction = {symbol["symbol"]: None for symbol in symbols_config}
start_prices = {symbol["symbol"]: fetch_start_price(symbol["symbol"]) for symbol in symbols_config}
trades_placed = {symbol["symbol"]: False for symbol in symbols_config}  # Track if a trade has been placed

def update_start_prices():
    global start_prices
    for symbol in symbols_config:
        symbol_name = symbol["symbol"]
        price = fetch_start_price(symbol_name)
        if price:
            start_prices[symbol_name] = price
            logging.info(f"Updated start price for {symbol_name}: {price}")
        else:
            logging.warning(f"Failed to update start price for {symbol_name}")

def determine_direction_with_range(pip_diff, positive_pip_diff, negative_pip_diff, positive_range, negative_range):
    if positive_pip_diff <= pip_diff <= positive_range:
        return "Upper"
    elif negative_range <= pip_diff <= negative_pip_diff:
        return "Down"
    else:
        return "Neutral"

def main_loop():
    """Main loop to check price differences with buffer range, place trades, and send notifications."""
    global last_hourly_check, current_direction, trades_placed

    logging.basicConfig(level=logging.INFO)

    if connect_mt5():
        while True:
            ist = pytz.timezone('Asia/Kolkata')
            current_time = datetime.now(ist)

            # Update start prices at 12 AM and reset trade placement flag
            if current_time.hour == 0 and current_time.minute == 0 and current_time.second == 0:
                update_start_prices()
                trades_placed = {symbol["symbol"]: False for symbol in symbols_config}  # Reset trade placement

            # Check price differences and send notifications
            for symbol in symbols_config:
                symbol_name = symbol["symbol"]
                pip_size = symbol["pip_size"]
                symbol_lot_size = symbol["lot_size"]
                positive_pip_diff = symbol["positive_pip_difference"]
                negative_pip_diff = symbol["negative_pip_difference"]
                positive_range = symbol["positive_pip_range"]
                negative_range = symbol["negative_pip_range"]

                try:
                    current_price = fetch_current_price(symbol_name)
                    start_price = fetch_start_price(symbol_name)

                    if current_price is None or start_price is None:
                        logging.warning(f"Price data unavailable for {symbol_name}")
                        continue

                    pip_diff = round((current_price - start_price) / pip_size, 3)

                    # Determine direction with buffer range
                    direction = determine_direction_with_range(
                        pip_diff, positive_pip_diff, negative_pip_diff, positive_range, negative_range
                    )

                    current_direction[symbol_name] = direction

                    # Trade placement logic (trades only placed once)
                    if direction == "Upper" and not trades_placed[symbol_name]:
                        logging.info(f"{symbol_name}: Entering positive range. Placing upward trade.")
                        place_trade_notify(symbol_name, "buy", symbol_lot_size)
                        send_discord_message(f"{symbol_name}-{direction}-{start_price}-{current_price}")
                        trades_placed[symbol_name] = True  # Mark trade as placed
                    elif direction == "Down" and not trades_placed[symbol_name]:
                        logging.info(f"{symbol_name}: Entering negative range. Placing downward trade.")
                        place_trade_notify(symbol_name, "sell", symbol_lot_size)
                        send_discord_message(f"{symbol_name}-{direction}-{start_price}-{current_price}")
                        trades_placed[symbol_name] = True  # Mark trade as placed

                    # Check if pip_diff equals the positive or negative threshold within the range
                    tolerance = 1e-6  # Small tolerance for floating point comparison

                    if (abs(pip_diff - positive_pip_diff) <= tolerance) and (positive_pip_diff <= pip_diff <= positive_range):
                        logging.info(f"{symbol_name}: pip_diff has reached the positive threshold of {positive_pip_diff}")
                        send_discord_message(f"{symbol_name}: pip_diff has reached the positive threshold of {positive_pip_diff}")

                    elif (abs(pip_diff - negative_pip_diff) <= tolerance) and (negative_range <= pip_diff <= negative_pip_diff):
                        logging.info(f"{symbol_name}: pip_diff has reached the negative threshold of {negative_pip_diff}")
                        send_discord_message(f"{symbol_name}: pip_diff has reached the negative threshold of {negative_pip_diff}")

                    # Send notifications when direction changes
                    if direction != "Neutral" and last_sent_direction[symbol_name] != direction:
                        data = {
                            "symbol": symbol_name,
                            "start_price": start_price,
                            "current_price": current_price,
                            "pip_difference": pip_diff,
                            "direction": direction
                        }
                        formatted_message = format_message("pip_difference", data)
                        logging.info(f"Formatted Message: {formatted_message}")
                        send_discord_message(formatted_message)

                        last_sent_direction[symbol_name] = direction
                except Exception as e:
                    logging.error(f"An error occurred for {symbol_name}: {e}")
                    continue

            # Hourly updates
            if time.time() - last_hourly_check > 3600:
                for symbol in symbols_config:
                    symbol_name = symbol["symbol"]
                    pip_size = symbol["pip_size"]
                    positive_pip_diff = symbol["positive_pip_difference"]
                    negative_pip_diff = symbol["negative_pip_difference"]
                    positive_range = symbol["positive_pip_range"]
                    negative_range = symbol["negative_pip_range"]

                    try:
                        current_price = fetch_current_price(symbol_name)
                        start_price = start_prices[symbol_name]

                        if current_price is None or start_price is None:
                            logging.warning(f"Price data unavailable for {symbol_name}")
                            continue

                        pip_diff = round((current_price - start_price) / pip_size, 3)
                        pips_to_positive_threshold = abs(round(positive_pip_diff - pip_diff, 3))
                        pips_to_negative_threshold = abs(round(pip_diff - negative_pip_diff, 3))

                        direction = determine_direction_with_range(
                            pip_diff, positive_pip_diff, negative_pip_diff, positive_range, negative_range
                        )

                        current_direction[symbol_name] = direction

                        # Trade placement logic in hourly update (trades only placed once)
                        if direction == "Upper" and not trades_placed[symbol_name]:
                            logging.info(f"{symbol_name}: Entering positive range. Placing upward trade.")
                            # place_trade(symbol_name, direction)
                            trades_placed[symbol_name] = True  # Mark trade as placed
                        elif direction == "Down" and not trades_placed[symbol_name]:
                            logging.info(f"{symbol_name}: Entering negative range. Placing downward trade.")
                            # place_trade(symbol_name, direction)
                            trades_placed[symbol_name] = True  # Mark trade as placed

                        data = {
                            "symbol": symbol_name,
                            "start_price": start_price,
                            "current_price": current_price,
                            "pip_difference": pip_diff,
                            "direction": direction,
                            "pips_to_positive_threshold": pips_to_positive_threshold,
                            "pips_to_negative_threshold": pips_to_negative_threshold
                        }
                        formatted_message = format_message("hourly_update", data)
                        logging.info(f"Hourly Update: {formatted_message}")
                        send_discord_message(formatted_message)
                    except Exception as e:
                        logging.error(f"An error occurred during hourly update for {symbol_name}: {e}")
                        continue

                last_hourly_check = time.time()

            time.sleep(1)

if __name__ == "__main__":
    main_loop()

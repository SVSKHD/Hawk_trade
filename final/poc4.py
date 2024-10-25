import MetaTrader5 as mt5
import pytz
from datetime import datetime, timedelta
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
entry_prices = {symbol["symbol"]: None for symbol in symbols_config}  # Track entry price of each trade

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

def place_trade(symbol_name, direction, lot_size, current_price):
    """Placeholder for placing a trade."""
    # Implement your trade placement logic here.
    logging.info(f"Placing trade for {symbol_name} in {direction} direction at {current_price}.")
    send_discord_message(f"Trade placed for {symbol_name} in {direction} direction at {current_price}.")
    entry_prices[symbol_name] = current_price  # Store entry price of the trade
    trades_placed[symbol_name] = True  # Mark trade as placed

def close_trade(symbol_name, direction, lot_size):
    """Placeholder for closing a trade."""
    logging.info(f"Closing trade for {symbol_name} in {direction} direction.")
    send_discord_message(f"Trade closed for {symbol_name} in {direction} direction.")
    close_trades_by_symbol(symbol_name)

def main_loop():
    """Main loop to check price differences, place trades, close trades, and send notifications."""
    global last_hourly_check, current_direction, trades_placed, entry_prices

    logging.basicConfig(level=logging.INFO)

    if connect_mt5():
        while True:
            ist = pytz.timezone('Asia/Kolkata')
            current_time = datetime.now(ist)

            # Update start prices at 12 AM and reset trade placement flag
            if current_time.hour == 0 and current_time.minute == 0 and current_time.second == 0:
                trades_placed = {symbol["symbol"]: False for symbol in symbols_config}  # Reset trade placement
                entry_prices = {symbol["symbol"]: None for symbol in symbols_config}  # Reset entry prices

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
                    start_price = start_prices[symbol_name]

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
                        place_trade(symbol_name, "buy", symbol_lot_size, current_price)
                    elif direction == "Down" and not trades_placed[symbol_name]:
                        logging.info(f"{symbol_name}: Entering negative range. Placing downward trade.")
                        place_trade(symbol_name, "sell", symbol_lot_size, current_price)

                    # Check if current price reaches the target for closing trades
                    if entry_prices[symbol_name] is not None:
                        target_up = entry_prices[symbol_name] + (5 * pip_size)
                        target_down = entry_prices[symbol_name] - (5 * pip_size)

                        if direction == "Upper" and current_price >= target_up:
                            logging.info(f"{symbol_name}: Reached target up price. Closing trade.")
                            close_trade(symbol_name, "buy", symbol_lot_size)
                            trades_placed[symbol_name] = False  # Reset trade status
                            entry_prices[symbol_name] = None  # Reset entry price

                        elif direction == "Down" and current_price <= target_down:
                            logging.info(f"{symbol_name}: Reached target down price. Closing trade.")
                            close_trade(symbol_name, "sell", symbol_lot_size)
                            trades_placed[symbol_name] = False  # Reset trade status
                            entry_prices[symbol_name] = None  # Reset entry price

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

            # Hourly updates (notifications only)
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
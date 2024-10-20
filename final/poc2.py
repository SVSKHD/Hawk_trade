# Configuration for symbols with buffer range
import MetaTrader5 as mt5
import pytz
from datetime import datetime, timedelta
from utils import fetch_current_price, fetch_start_price, connect_mt5, format_message
from notifications import send_discord_message
import time
from trade_management import place_trade, close_trades_by_symbol


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

def determine_direction_with_range(pip_diff, positive_pip_diff, negative_pip_diff, positive_range, negative_range):
    """Determine direction considering the range for pip difference."""
    if positive_pip_diff <= pip_diff <= positive_range:
        return "Upper"
    elif negative_range <= pip_diff <= negative_pip_diff:
        return "Down"
    else:
        return "Neutral"

def main_loop():
    """Main loop to check price differences with buffer range and send notifications."""
    global last_hourly_check, current_direction

    if connect_mt5():
        while True:
            ist = pytz.timezone('Asia/Kolkata')
            current_time = datetime.now(ist)

            # Check price differences and send notifications
            for symbol in symbols_config:
                symbol_name = symbol["symbol"]
                pip_size = symbol["pip_size"]
                positive_pip_diff = symbol["positive_pip_difference"]
                negative_pip_diff = symbol["negative_pip_difference"]
                positive_range = symbol["positive_pip_range"]
                negative_range = symbol["negative_pip_range"]

                current_price = fetch_current_price(symbol_name)
                start_price = fetch_start_price(symbol_name)

                if current_price and start_price:
                    pip_diff = round((current_price - start_price) / pip_size, 3)

                    # Determine direction with buffer range
                    direction = determine_direction_with_range(
                        pip_diff, positive_pip_diff, negative_pip_diff, positive_range, negative_range
                    )

                    current_direction[symbol_name] = direction

                    if direction != "Neutral" and last_sent_direction[symbol_name] != direction:
                        data = {
                            "symbol": symbol_name,
                            "start_price": start_price,
                            "current_price": current_price,
                            "pip_difference": pip_diff,
                            "direction": direction
                        }
                        formatted_message = format_message("pip_difference", data)
                        print(f"Formatted Message: {formatted_message}")
                        send_discord_message(formatted_message)

                        last_sent_direction[symbol_name] = direction

            # Hourly updates (same as before)
            if time.time() - last_hourly_check > 3600:
                for symbol in symbols_config:
                    symbol_name = symbol["symbol"]
                    pip_size = symbol["pip_size"]
                    positive_pip_diff = symbol["positive_pip_difference"]
                    negative_pip_diff = symbol["negative_pip_difference"]
                    positive_range = symbol["positive_pip_range"]
                    negative_range = symbol["negative_pip_range"]

                    current_price = fetch_current_price(symbol_name)
                    start_price = fetch_start_price(symbol_name)

                    if current_price and start_price:
                        pip_diff = round((current_price - start_price) / pip_size, 3)
                        pips_to_positive_threshold = round(positive_pip_diff - pip_diff, 3)
                        pips_to_negative_threshold = round(pip_diff - negative_pip_diff, 3)

                        direction = determine_direction_with_range(
                            pip_diff, positive_pip_diff, negative_pip_diff, positive_range, negative_range
                        )

                        if pips_to_positive_threshold:
                            print(f"{symbol_name}-{pips_to_negative_threshold}-{direction}")
                        elif pips_to_negative_threshold:
                            print(f"{symbol_name}-{pips_to_negative_threshold}-{direction}")

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
                        print(f"Hourly Update: {formatted_message}")
                        send_discord_message(formatted_message)

                last_hourly_check = time.time()

            time.sleep(1)

if __name__ == "__main__":
    main_loop()

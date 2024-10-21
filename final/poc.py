import MetaTrader5 as mt5
import pytz
from datetime import datetime, timedelta
from utils import fetch_current_price, fetch_start_price, connect_mt5
from notifications import send_discord_message
import time

# Configuration for symbols
symbols_config = [
    {
        "symbol": "BTCUSD",
        "positive_pip_difference": 50,
        "negative_pip_difference": -50,
        "close_trade_at": 10,
        "close_trade_at_opposite_direction": 7,
        "pip_size": 1,
        "lot_size": 1.0
    },
    {
        "symbol": "EURUSD",
        "positive_pip_difference": 1,
        "negative_pip_difference": -1,
        "close_trade_at": 10,
        "close_trade_at_opposite_direction": 8,
        "pip_size": 0.0001,
        "lot_size": 1.0
    },
    {
        "symbol": "GBPUSD",
        "positive_pip_difference": 15,
        "negative_pip_difference": -15,
        "close_trade_at": 10,
        "close_trade_at_opposite_direction": 8,
        "pip_size": 0.0001,
        "lot_size": 1.0
    },
    {
        "symbol": "USDJPY",
        "positive_pip_difference": 1,
        "negative_pip_difference": -1,
        "close_trade_at": 10,
        "close_trade_at_opposite_direction": 7,
        "pip_size": 0.01,
        "lot_size": 1.0
    }
]

# State tracking
last_sent_direction = {symbol["symbol"]: None for symbol in symbols_config}
last_hourly_check = time.time()
current_direction = {symbol["symbol"]: None for symbol in symbols_config}  # Global variable for direction

def main_loop():
    """Main loop to check price differences and send notifications."""
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

                current_price = fetch_current_price(symbol_name)
                start_price = fetch_start_price(symbol_name)  # Fetch start price each time

                if current_price and start_price:
                    pip_diff = round((current_price - start_price) / pip_size, 3)

                    # Determine direction based on pip difference and thresholds
                    if pip_diff >= positive_pip_diff:
                        direction = "Upper"
                    elif pip_diff <= negative_pip_diff:
                        direction = "Down"
                    else:
                        direction = "Neutral"

                    current_direction[symbol_name] = direction  # Store direction globally

                    if direction != "Neutral" and last_sent_direction[symbol_name] != direction:
                        formatted_message = {
                            "symbol": symbol_name,
                            "start_price": start_price,
                            "current_price": current_price,
                            "pip_difference": pip_diff,
                            "direction": direction
                        }
                        print(f"Formatted Message: {formatted_message}")
                        send_discord_message(f"pip-difference {formatted_message}")

                        last_sent_direction[symbol_name] = direction

            # Hourly updates
            if time.time() - last_hourly_check > 3600:
                for symbol in symbols_config:
                    symbol_name = symbol["symbol"]
                    pip_size = symbol["pip_size"]
                    positive_pip_diff = symbol["positive_pip_difference"]
                    negative_pip_diff = symbol["negative_pip_difference"]

                    current_price = fetch_current_price(symbol_name)
                    start_price = fetch_start_price(symbol_name)

                    if current_price and start_price:
                        pip_diff = round((current_price - start_price) / pip_size, 3)
                        pips_to_positive_threshold = round(positive_pip_diff - pip_diff, 3)
                        pips_to_negative_threshold = round(pip_diff - negative_pip_diff, 3)

                        # Determine direction
                        if pip_diff >= positive_pip_diff:
                            direction = "Upper"
                        elif pip_diff <= negative_pip_diff:
                            direction = "Down"
                        else:
                            direction = "Neutral"

                        current_direction[symbol_name] = direction  # Update direction globally

                        formatted_message = {
                            "symbol": symbol_name,
                            "start_price": start_price,
                            "current_price": current_price,
                            "pip_difference": pip_diff,
                            "direction": direction,
                            "pips_to_positive_threshold": pips_to_positive_threshold,
                            "pips_to_negative_threshold": pips_to_negative_threshold
                        }
                        print(f"Hourly Update: {formatted_message}")
                        send_discord_message(f"Hourly_update {formatted_message}")

                last_hourly_check = time.time()

            time.sleep(1)

if __name__ == "__main__":
    main_loop()
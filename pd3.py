import os
import json

current_dir = os.path.dirname(os.path.abspath(__file__))

# Create the full path to details.json
details_path = os.path.join(current_dir, 'details.json')

# Load details from details.json
with open(details_path) as f:
    config = json.load(f)

symbols = config['symbols']

# Test prices: simulate both up and down movements after the first threshold
prices = [1.09508, 1.09418, 1.09408, 1.09388, 1.09375, 1.09360, 1.09345, 1.09390, 1.09430, 1.09460, 1.09530]


def get_symbol_data(symbol, symbol_data):
    for sym in symbol_data:
        if sym['symbol'] == symbol:
            return sym
    return None


def pip_difference(symbol, start_price, current_price, pip_threshold, thresholds, threshold_count, last_direction):
    symbol_data = get_symbol_data(symbol, symbols)
    if not symbol_data:
        print(f"Symbol {symbol} not found in details.json")
        return threshold_count, last_direction

    if not thresholds:  # If no threshold is reached yet, start with the start_price
        previous_threshold_price = start_price
    else:
        previous_threshold_price = thresholds[-1]  # Use the last reached threshold price

    result_from_start = current_price - start_price  # Calculate pip movement from start price
    result_from_previous = current_price - previous_threshold_price  # Calculate from last threshold

    # Determine pip size based on the symbol
    if 'JPY' in symbol:
        pip_size = 0.01
    elif symbol in ['XAUUSD', 'XAGUSD']:  # Gold and Silver
        pip_size = 0.1  # Gold and silver pip size is usually 0.1
    else:
        pip_size = 0.0001

    # Calculate the pip difference from the start price and the previous threshold
    pips_from_start = round(result_from_start / pip_size)
    pips_from_previous = round(result_from_previous / pip_size)

    # Determine the direction
    direction = "down" if pips_from_previous < 0 else "up"

    # Define a tolerance range for closing trades (e.g., ±5 pips range)
    tolerance_range = 5

    # Check if the pip difference from the previous threshold is greater than or equal to the pip threshold
    if abs(pips_from_previous) >= pip_threshold:
        if not thresholds:  # This is the first threshold being reached
            print(
                f"hello first threshold reached for {symbol} at {current_price} ({pips_from_previous} pips) in the {direction} direction.")
        else:
            # After the first threshold, check for opposite or same direction
            if direction != last_direction:
                # Check if pips_from_previous is greater than or within tolerance of close_trade_at_opposite_direction
                if symbol_data.get('close_trade_at_opposite_direction') and abs(pips_from_previous) >= (
                        symbol_data.get('close_trade_at_opposite_direction') - tolerance_range):
                    print("hello trade is closed due to opposite direction threshold.")
                print(
                    f"Threshold breach: {symbol} has changed direction to {direction} with {pips_from_previous} pips movement.")
                print(f"Threshold breach - {symbol}: {symbol_data}")
            else:
                # Check if pips_from_previous is greater than or within tolerance of close_trade_at
                if symbol_data.get('close_trade_at') and abs(pips_from_previous) >= (
                        symbol_data.get('close_trade_at') - tolerance_range):
                    print(f"Trade closed at {pips_from_previous} pips in the same direction.")
                print(
                    f"Threshold continuation: {symbol} continues moving {direction} with {pips_from_previous} pips movement.")
                print(f"Threshold continuation - {symbol}: {symbol_data}")

        print(
            f"{symbol} has moved {abs(pips_from_previous)} pips in the {direction} direction, exceeding the {pip_threshold} pip threshold.")
        thresholds.append(current_price)  # Append the current price as the new threshold
        threshold_count += 1  # Increment the threshold count
        print(
            f"New threshold added for {symbol} at {current_price}. Total thresholds reached: {threshold_count}. Current list of thresholds: {thresholds}")

        # Update last direction
        last_direction = direction
    else:
        print(
            f"{symbol} has moved {pips_from_previous} pips from the last threshold, which is less than the {pip_threshold} pip threshold.")

    # Always print the pips movement from the start price
    print(f"{symbol} moved {pips_from_start} pips from the start price {start_price}. Current Thresholds: {thresholds}")

    return threshold_count, last_direction  # Return the updated threshold count and last direction


# Initialize the threshold list, threshold count, and last direction
thresholds = []
threshold_count = 0
last_direction = None

# Test the function with the loop for the provided prices
for price in prices:
    threshold_count, last_direction = pip_difference("EURUSD", 1.09717, price, 15, thresholds, threshold_count,
                                                     last_direction)

# Output the final threshold list and the total count of thresholds
print("Final threshold reached prices:", thresholds)
print(f"Total number of thresholds reached: {threshold_count}")

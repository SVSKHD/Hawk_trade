import os
import json

current_dir = os.path.dirname(os.path.abspath(__file__))

# Create the full path to details.json
details_path = os.path.join(current_dir, 'details.json')

# Load details from details.json
with open(details_path) as f:
    config = json.load(f)

symbols = config['symbols']

prices = [1.09508, 1.09418, 1.09408, 1.09388, 1.09375, 1.09360, 1.09345]

def pip_difference(symbol, start_price, current_price, pip_threshold, thresholds):
    if not thresholds:  # If no threshold is reached yet, start with the start_price
        previous_threshold_price = start_price
    else:
        previous_threshold_price = thresholds[-1]  # Use the last reached threshold price

    result_from_start = current_price - start_price  # Calculate pip movement from start price
    result_from_previous = current_price - previous_threshold_price  # Calculate from last threshold

    if 'JPY' in symbol:
        pip_size = 0.01
    elif symbol in ['XAUUSD', 'XAGUSD']:  # Gold and Silver
        pip_size = 0.1  # Gold and silver pip size is usually 0.1
    else:
        pip_size = 0.0001

        # Calculate the pip difference from the start price and the previous threshold
    pips_from_start = round(result_from_start / pip_size)
    pips_from_previous = round(result_from_previous / pip_size)

    # Check if the pip difference from the previous threshold is greater than or equal to the pip threshold
    if abs(pips_from_previous) >= pip_threshold:
        if not thresholds:  # This is the first threshold being reached
            print(f"hello first threshold reached for {symbol} at {current_price} {pips_from_previous}")

        if pips_from_previous < 0:
            direction = "down"
            print(f"{symbol} has moved {abs(pips_from_previous)} pips in the {direction} direction, exceeding the {pip_threshold} pip threshold.")
        elif pips_from_previous > 0:
            direction = "up"
            print(f"{symbol} has moved {pips_from_previous} pips in the {direction} direction, exceeding the {pip_threshold} pip threshold.")
        thresholds.append(current_price)  # Append the current price as the new threshold
    else:
        print(f"{symbol} has moved {pips_from_previous} pips from the last threshold, which is less than the {pip_threshold} pip threshold.")

    # Always print the pips movement from the start price
    print(f"{symbol} moved {pips_from_start} pips from the start price {start_price}. Current Thresholds: {thresholds}")

# Initialize the threshold list
thresholds = []

# Test the function with the loop for the provided prices
for price in prices:
    pip_difference("EURUSD", 1.09717, price, 15, thresholds)

# Output the final threshold list
print("Final threshold reached prices:", thresholds)


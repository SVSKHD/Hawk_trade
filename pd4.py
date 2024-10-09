def pip_difference(symbol, start_price, current_price, upper_thresholds=None, lower_thresholds=None):
    if upper_thresholds is None:
        upper_thresholds = []
    if lower_thresholds is None:
        lower_thresholds = []

    result = current_price - start_price
    fr = None

    # Adjust for the pip value based on the symbol
    if symbol in ["EURUSD", "GBPUSD"]:
        fr = result / 0.0001  # Adjusting for 4 decimal places (1 pip = 0.0001)
    elif symbol in ["USDJPY", "EURJPY"]:
        fr = result / 0.01  # Adjusting for 2 decimal places (1 pip = 0.01)

    # Check for threshold crossing for upper thresholds (buy trade)
    if fr >= 15:
        upper_thresholds.append(current_price)
        if len(upper_thresholds) == 1:
            print(f"hello buy trade at price: {upper_thresholds[0]}")
        elif len(upper_thresholds) > 1:
            # Compare the first threshold value with the current price for pip difference
            initial_pip_difference = (current_price - upper_thresholds[0]) / 0.0001

            # Use a tolerance for floating-point precision issues
            tolerance = 0.0001

            if abs(initial_pip_difference - 5) < tolerance or abs(initial_pip_difference + 5) < tolerance:
                print(f"Close buy trade: trades closed at {current_price}")

            print(f"Current price: {current_price}, First upper threshold: {upper_thresholds[0]}, "
                  f"Pip Difference: {initial_pip_difference}")

    # Check for threshold crossing for lower thresholds (sell trade)
    elif fr <= -15:
        lower_thresholds.append(current_price)
        if len(lower_thresholds) == 1:
            print(f"hello sell trade at price: {lower_thresholds[0]}")
        elif len(lower_thresholds) > 1:
            # Compare the first threshold value with the current price for pip difference
            initial_pip_difference = (lower_thresholds[0] - current_price) / 0.0001

            # Use a tolerance for floating-point precision issues
            tolerance = 0.0001

            if abs(initial_pip_difference - 5) < tolerance or abs(initial_pip_difference + 5) < tolerance:
                print(f"Close sell trade: trades closed at {current_price}")

            print(f"Current price: {current_price}, First lower threshold: {lower_thresholds[0]}, "
                  f"Pip Difference: {initial_pip_difference}")

    return {"fr": fr, "upper_thresholds": upper_thresholds, "lower_thresholds": lower_thresholds, "current_price": current_price}


prices = [1.0911, 1.09, 1.0890, 1.0895, 1.087, 1.09123]

upper = []
lower = []

for price in prices:
    result=pip_difference("EURUSD", 1.09123, price, upper, lower)
    print(result)
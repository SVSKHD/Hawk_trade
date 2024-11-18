async def calculate_pip_difference(start_price, current_price):
    result = current_price - start_price
    return result

async def calculate_thresholds(symbol, difference):
    symbol_name = symbol["symbol"]
    symbol_pip = symbol["pip_size"]
    data = {"name":symbol_name, "thresholds":0}
    if difference:
        data["thresholds"] = difference/symbol_pip
        return data

async def check_thresholds(symbol, pip_difference):
    symbol_name = symbol["symbol"]
    symbol_pip_size = symbol["pip_size"]
    format_threshold = pip_difference / symbol_pip_size
    no_of_thresholds_reached = format_threshold/abs(pip_difference)
    positive_difference = symbol["positive_pip_difference"]
    negative_difference = symbol["negative_pip_difference"]

    data = {"symbol": symbol_name, "direction": "neutral", "thresholds": no_of_thresholds_reached}


    if format_threshold >= positive_difference:
        data["direction"] = "up"
        no_of_thresholds_reached += 1
        data["thresholds"] = no_of_thresholds_reached
        print(f"positive threshold {data}")

    elif format_threshold <= negative_difference:
        data["direction"] = "down"
        no_of_thresholds_reached += 1
        data["thresholds"] = no_of_thresholds_reached
        print(f"negative threshold {data}")

    else:
        data["direction"] = "neutral"
        data["thresholds"] = no_of_thresholds_reached
        print(f"neutral {data}")

    return data

async def check_and_confirm_trades(symbol, thresholds):
    symbol_name = symbol["symbol"]
    if thresholds >= 1:
        print(f"Place Trade Initiated for {symbol_name}")

async def check_trades_confirm_hedging(symbol, thresholds):
    symbol_name = symbol["symbol"]
    if thresholds <= 0.5:
        print(f"Hedging Started for {symbol_name}")

async def process_symbol(symbol, start_price, current_price):
    pip_difference = await calculate_pip_difference(start_price, current_price)
    data = await check_thresholds(symbol, pip_difference)
    thresholds = data['thresholds']
    await check_and_confirm_trades(symbol, thresholds)
    await check_trades_confirm_hedging(symbol, thresholds)


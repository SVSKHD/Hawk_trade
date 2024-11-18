import asyncio
from config import symbols_config

eurusd = {
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

current_prices=[
1.094099,
1.095099,
1.096099,
1.097099,
1.098099,
1.099099,
1.093099,
1.092099,
1.092199,
1.092219
]

async def calculate_pip_difference(current_price, start_price):
    result = current_price-start_price
    return result


async def test_calculate_pip_difference(symbol):
    pip_difference = await calculate_pip_difference(1.094099, 1.096799)
    result = pip_difference / symbol['pip_size']
    return result


async def check_thresholds(symbol):
    pip_difference = await test_calculate_pip_difference(symbol)
    no_of_thresholds = pip_difference / symbol["positive_pip_difference"]
    data = {"symbol": symbol["symbol"], "thresholds": no_of_thresholds}
    print("Number of Thresholds:", no_of_thresholds)  # Display the result
    return data


async def check_threshold_and_hedging(symbol, pip_difference):
    symbol_name = symbol["symbol"]
    if pip_difference>=0.5:
        print(f"Hedging has begin for {symbol_name}")





async def trigger_trade_by_threshold(symbol):
    threshold_data = await check_thresholds(symbol)
    no_of_thresholds = round(threshold_data["thresholds"],2)

    if no_of_thresholds > 0:
        print("Positive Trade")
        if no_of_thresholds>=1:
            print(f"Positive Threshold reached place Trade {no_of_thresholds}")
            hedging=await check_threshold_and_hedging(symbol, no_of_thresholds)
            print("hedging", hedging)
    else:
        print("Negative Trade")
        if no_of_thresholds<-1:
            print(f"Negative Threshold reached place Trade {no_of_thresholds}")
            hedging= await check_threshold_and_hedging(symbol, no_of_thresholds)
            print("hedging", hedging)


for price in current_prices:
    print("current-price",price)

# Run the test function within the same event loop
asyncio.run(trigger_trade_by_threshold(eurusd))

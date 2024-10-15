from datetime import datetime

import MetaTrader5 as mt5
from notifications import send_discord_message

def place_trade_notify(symbol, action, lot_size):
    # Ensure MT5 is initialized
    if not mt5.initialize():
        print("Failed to initialize MetaTrader 5")
        return

    print(f"Initialized MetaTrader 5 for trading with symbol {symbol}")

    # Check for initialization errors
    print(f"Initialization error: {mt5.last_error()}")

    # Ensure the symbol is available
    if not mt5.symbol_select(symbol, True):
        print(f"Failed to select symbol {symbol}")
        mt5.shutdown()
        return

    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"Symbol info not available for {symbol}")
        mt5.shutdown()
        return

    # Get the latest price for the symbol
    price_info = mt5.symbol_info_tick(symbol)
    if price_info is None:
        print(f"Failed to get tick information for {symbol}")
        mt5.shutdown()
        return

    # Set price based on buy or sell action
    price = price_info.bid
    print(f"Price for {action}: {price}")
    lot = lot_size if lot_size is not None else 1.0
    print(f"Lot size: {lot}")
    deviation = 50  # Increase deviation to account for price changes
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": mt5.ORDER_TYPE_BUY if action == 'buy' else mt5.ORDER_TYPE_SELL,
        "price": price,
        "deviation": deviation,
        "magic": 234000,
        "comment": "python script open",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,  # Try ORDER_FILLING_IOC
    }

    print("Request parameters:", request)

    # Send the trade request
    result = mt5.order_send(request)

    # Check the result and print details
    if result is None:
        print("Order send failed: no result returned")
        send_discord_message(f"Order send error when it is none for clear error description: {mt5.last_error()}")
    else:
        print("Order send result:")
        print(f"  retcode: {result.retcode}")
        print(f"  deal: {result.deal}")
        print(f"  order: {result.order}")
        print(f"  price: {result.price}")
        print(f"  comment: {result.comment}")
        print(f"  request_id: {result.request_id}")
        print(f"  bid: {result.bid}")
        print(f"  ask: {result.ask}")
        print(f"  volume: {result.volume}")
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"Trade request failed, retcode={result.retcode}")
        else:
            now = datetime.now()
            send_discord_message(f"Trade executed successfully at {now}, order={result}")

    # Shutdown the connection
    mt5.shutdown()

# Example usage
place_trade_notify("EURUSD", "buy", 3.0)

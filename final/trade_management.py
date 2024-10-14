import MetaTrader5 as mt5
from notifications import send_discord_message


def place_trade(symbol, order_type, volume, price):
    print(f"Attempting to place trade: {symbol} {order_type} {volume} lots at {price}")

    # Ensure MetaTrader 5 is initialized
    if not mt5.initialize():
        print("Failed to initialize MetaTrader 5")
        return

    # Ensure the symbol is available for trading
    if not mt5.symbol_select(symbol, True):
        print(f"Failed to select symbol: {symbol}")
        return

    # Fetch tick data for the symbol
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print(f"Failed to retrieve tick data for {symbol}")
        return

    # Set price based on buy/sell action
    price = tick.ask if order_type == "buy" else tick.bid
    deviation = 20  # Allow some slippage

    # Define the order request
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": mt5.ORDER_TYPE_BUY if order_type == "buy" else mt5.ORDER_TYPE_SELL,
        "price": price,
        "deviation": deviation,
        "magic": 234000,
        "comment": "python script open",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }

    print("Trade request:", request)

    # Send the trading request
    result = mt5.order_send(request)

    # Check the result
    if result is None:
        print(f"Trade failed: MetaTrader 5 API returned None for {symbol}")
        return
    elif result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Trade failed for {symbol}. Return code: {result.retcode}")
        print(f"Error details: {result}")
    else:
        print(f"Trade placed successfully: {result}")


def close_all_trades():
    # Initialize connection to MetaTrader 5
    if not mt5.initialize():
        print("Failed to initialize MT5, error code:", mt5.last_error())
        return

    # Retrieve open positions
    open_positions = mt5.positions_get()

    if open_positions is None or len(open_positions) == 0:
        print("No open positions.")
        return

    # Loop through each open position and close it
    for position in open_positions:
        symbol = position.symbol
        ticket = position.ticket
        lot = position.volume

        # Determine the type of trade (buy or sell) to create the opposite order
        if position.type == mt5.ORDER_TYPE_BUY:
            trade_type = mt5.ORDER_TYPE_SELL
        elif position.type == mt5.ORDER_TYPE_SELL:
            trade_type = mt5.ORDER_TYPE_BUY
        else:
            print(f"Unknown position type for ticket {ticket}.")
            continue

        # Create close request
        close_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": trade_type,
            "position": ticket,
            "deviation": 20,
            "magic": 123456,  # Your unique identifier for trades
            "comment": "Hawk Closing trade",
        }

        # Send close order
        result = mt5.order_send(close_request)

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"Failed to close trade {ticket}, error code: {result}")
        else:
            print(f"Successfully closed trade {ticket}.")


def close_trades_by_symbol(symbol):
    # Ensure MT5 is initialized
    if not mt5.initialize():
        print("Failed to initialize MT5, error code:", mt5.last_error())
        return

    # Retrieve open positions for the specified symbol
    open_positions = mt5.positions_get(symbol=symbol)

    if open_positions is None or len(open_positions) == 0:
        print(f"No open positions for {symbol}.")
        return

    # Loop through each open position and close it
    for position in open_positions:
        ticket = position.ticket
        lot = position.volume

        # Determine the type of trade (buy or sell) to create the opposite order
        if position.type == mt5.ORDER_TYPE_BUY:
            trade_type = mt5.ORDER_TYPE_SELL
        elif position.type == mt5.ORDER_TYPE_SELL:
            trade_type = mt5.ORDER_TYPE_BUY
        else:
            print(f"Unknown position type for ticket {ticket}.")
            continue

        # Get current price for closing
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            print(f"Symbol {symbol} not found.")
            continue

        price = symbol_info.bid if trade_type == mt5.ORDER_TYPE_SELL else symbol_info.ask

        # Create close request
        close_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": trade_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": 123456,  # Your unique identifier for trades
            "comment": "Closing trade by script",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }

        # Send close order
        result = mt5.order_send(close_request)

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            message=f"Failed to close trade {ticket} for {symbol}, error code: {result} from tarde_management"
            print(message)
            send_discord_message(message)
        else:
            message=f"Successfully closed trade {ticket} for {symbol}. from trade_management"
            print(message)
            send_discord_message(message)

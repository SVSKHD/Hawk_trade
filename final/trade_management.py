import MetaTrader5 as mt5
from notifications import send_discord_message


def place_trade(symbol, order_type, volume, price=None, slippage=20, stop_loss=None, take_profit=None):
    """
    Places a trade order in MetaTrader 5.
    """
    # Ensure symbol is selected
    if not mt5.symbol_select(symbol, True):
        error_message = f"Failed to select {symbol} for trading."
        print(error_message)
        return error_message

    # Get symbol info
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        error_message = f"Symbol {symbol} not found, cannot trade."
        print(error_message)
        return error_message

    # If the symbol is unavailable for trading
    if not symbol_info.visible:
        if not mt5.symbol_select(symbol, True):
            error_message = f"Symbol {symbol} is not visible, could not select."
            print(error_message)
            return error_message

    # Determine price if not provided
    if price is None or price == 0:
        if order_type == mt5.ORDER_TYPE_BUY:
            price = mt5.symbol_info_tick(symbol).ask
        else:
            price = mt5.symbol_info_tick(symbol).bid

    # Prepare the order request
    order_request = {
        "action": mt5.TRADE_ACTION_DEAL,  # Correct action for market order
        "symbol": symbol,
        "volume": volume,
        "type": order_type,  # Correct order type
        "price": price,
        "deviation": slippage,  # Correct field name
        "magic": 0,
        "comment": "Raven Algo Trade",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }

    # Include stop_loss and take_profit if provided
    if stop_loss is not None:
        order_request['sl'] = stop_loss
    if take_profit is not None:
        order_request['tp'] = take_profit

    # Send the order
    result = mt5.order_send(order_request)

    # Check if the order was placed successfully
    if result is None:
        # If result is None, retrieve the last error
        error_code, error_message = mt5.last_error()
        error_msg = f"Order send failed, error code: {error_code}, message: {error_message}"
        print(error_msg)
        return error_msg

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        error_msg = f"Order failed, retcode={result.retcode}, comment={result.comment}"
        print(error_msg)
        return error_msg

    success_msg = f"Order placed successfully, order ticket={result.order}"
    print(success_msg)
    return success_msg


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
            "comment": "Closing trade",
        }

        # Send close order
        result = mt5.order_send(close_request)

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"Failed to close trade {ticket}, error code: {result.retcode}")
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
            print(f"Failed to close trade {ticket} for {symbol}, error code: {result.retcode}")
        else:
            print(f"Successfully closed trade {ticket} for {symbol}.")
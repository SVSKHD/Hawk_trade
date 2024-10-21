import MetaTrader5 as mt5
import pytz
from datetime import datetime, timedelta
from notifications import send_discord_message

def connect_mt5():
    if not mt5.initialize():
        print("Failed to initialize MetaTrader5")
        return False
    login = 213171528  # Login provided
    password = "AHe@Yps3"  # Password provided
    server = "OctaFX-Demo"  # Server provided

    authorized = mt5.login(login, password=password, server=server)
    if not authorized:
        print(f"Login failed for account {login}")
        return False
    print(f"Successfully logged into account {login} on server {server}")
    return True



def fetch_current_price(symbol):
    tick = mt5.symbol_info_tick(symbol)
    if tick:
        return tick.bid  # or tick.ask depending on your logic
    else:
        print(f"Failed to get current price for {symbol}")
        return None


def fetch_start_price(symbol):
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)

    start_price = None

    if now.weekday() == 0:  # Monday
        start_price = fetch_friday_closing_price(symbol)
    else:
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        utc_from = start_of_day.astimezone(pytz.utc)

        rates = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M5, utc_from, 1)

        if rates is not None and len(rates) > 0:
            start_price = rates[0]['close']
        else:
            print(f"Failed to get start price for {symbol}")
            return None

    if start_price:
        print(f"Fetched start price for {symbol}: {start_price}")

    return start_price


def fetch_friday_closing_price(symbol):
    today = datetime.now(pytz.timezone('Asia/Kolkata'))
    days_ago = (today.weekday() + 3) % 7 + 2
    last_friday = today - timedelta(days=days_ago)
    last_friday = last_friday.replace(hour=23, minute=59, second=59)
    utc_from = last_friday.astimezone(pytz.utc)

    rates = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M5, utc_from, 1)
    if rates is not None and len(rates) > 0:
        closing_price = rates[0]['close']
        print(f"Fetched last Friday's closing price for {symbol}: {closing_price}")
        return closing_price
    print(f"Failed to get last Friday's closing price for {symbol}")
    return None


def place_trade_notify(symbol, action, lot_size):
    # Ensure MT5 is initialized
    if not mt5.initialize():
        print("Failed to initialize MetaTrader 5")
        return

    print(f"Initialized MetaTrader 5 for trading with symbol {symbol}")

    # Ensure the symbol is available
    if not mt5.symbol_select(symbol, True):
        print(f"Failed to select symbol {symbol}")
        mt5.shutdown()
        return

    # Get the latest price for the symbol
    price_info = mt5.symbol_info_tick(symbol)
    if price_info is None:
        print(f"Failed to get tick information for {symbol}")
        mt5.shutdown()
        return

    # Set price based on buy or sell action
    price = price_info.ask if action == 'buy' else price_info.bid
    print(f"Price for {action}: {price}")

    # Define request parameters
    lot = lot_size if lot_size is not None else 1.0
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
        "type_filling": mt5.ORDER_FILLING_FOK,  # You can also try mt5.ORDER_FILLING_IOC
    }

    print("Request parameters:", request)

    # Send the trade request
    result = mt5.order_send(request)

    # Check the result and print details
    if result is None:
        print("Order send failed: no result returned")
        send_discord_message(f"Order send error: {mt5.last_error()}")
    else:
        print("Order send result:")
        print(f"  retcode: {result.retcode}")
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"Trade request failed, retcode={result.retcode}")
            send_discord_message(f"Trade request failed for {symbol}, retcode={result.retcode}")
        else:
            now = datetime.now()
            send_discord_message(f"Trade executed successfully at {now}, order={result}")



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



def format_message(message_type, data):
    """Format messages for notifications and hourly updates."""
    direction_symbols = {"Upper": "↑", "Down": "↓", "Neutral": "-"}
    direction_symbol = direction_symbols.get(data["direction"], "-")

    if message_type == "pip_difference":
        formatted_message = f"""

**{data["symbol"]} {direction_symbol}**

**Start Price:** **{data["start_price"]}**
**Current Price:** **{data["current_price"]}**
**Pip Difference:** **{data["pip_difference"]}**
**Direction:** {direction_symbol} {data["direction"]}

"""
        return formatted_message.strip()
    elif message_type == "hourly_update":
        formatted_message = f"""

--------------------------------------------------Hourly Update--------------------------------------------------

**Symbol:** {data["symbol"]}
**Start Price:** **{data["start_price"]}**
**Current Price:** **{data["current_price"]}**
**Pip Difference:** **{data["pip_difference"]}**
**Direction:** {direction_symbol} {data["direction"]}

**Pips to Positive Threshold:** {data["pips_to_positive_threshold"]}
**Pips to Negative Threshold:** {data["pips_to_negative_threshold"]}

"""
        return formatted_message.strip()
    else:
        return str(data)

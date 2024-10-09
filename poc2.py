# db.py
from pymongo import MongoClient
import pytz
from datetime import datetime
from notifications import send_discord_message

# MongoDB setup
MONGO_URI = 'mongodb+srv://hithesh:hithesh@utbiz.npdehas.mongodb.net/'
client = MongoClient(MONGO_URI)
db = client['pip_tracking_db']
ist = pytz.timezone('Asia/Kolkata')


# Function to save or update threshold data in MongoDB
def save_or_update_threshold_in_mongo(symbol, start_price, current_price, previous_threshold, pips_from_start,
                                      direction, thresholds_list, timestamp, start_price_time):
    collection_name = "pip_check2"
    pip_check_collection = db[collection_name]

    # Ensure the timestamp and start_price_time are timezone-aware
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=pytz.utc)
    if start_price_time.tzinfo is None:
        start_price_time = start_price_time.replace(tzinfo=pytz.utc)

    # Convert to IST for display and storage purposes
    current_date_ist = timestamp.astimezone(ist).strftime('%Y-%m-%d %H:%M:%S')
    start_price_time_ist = start_price_time.astimezone(ist).strftime('%Y-%m-%d %H:%M:%S')

    # Check if the threshold already exists in MongoDB
    existing_data = pip_check_collection.find_one({
        "symbol": symbol,
        "start_price": start_price,
        "initial_threshold_price": current_price
    })

    if existing_data:
        print(f"Threshold for {symbol} with price {current_price} already exists. Skipping insertion.")
        return

    # Create the query and data structure for upserting
    query = {"symbol": symbol, "date": current_date_ist.split()[0]}

    threshold_data = {
        "symbol": symbol,
        "start_price": start_price,
        "start_price_time": start_price_time_ist,
        "initial_threshold_price": current_price,
        "previous_threshold": previous_threshold,
        "pips_from_start": pips_from_start,
        "direction": direction,
        "timestamp": current_date_ist,
        "trade_placed": {"status": "Pending", "trade_error": None}
    }

    update_data = {
        "$set": threshold_data,
        "$addToSet": {"thresholds_list": {"$each": thresholds_list}}
    }

    try:
        result = pip_check_collection.update_one(query, update_data, upsert=True)

        if result.matched_count > 0:
            message = f"Updated existing document for {symbol} on {current_date_ist}. Data saved successfully."
        else:
            message = f"Inserted new document for {symbol} on {current_date_ist}. Data saved successfully."

        print(message)
        send_discord_message(message)

    except Exception as e:
        error_message = f"Failed to save/update document for {symbol} on {current_date_ist}: {str(e)}"
        print(error_message)
        send_discord_message(error_message)


# Function to check if data already exists in MongoDB
def check_data_exists_in_mongo(symbol, date):
    collection_name = "pip_check2"
    pip_check_collection = db[collection_name]

    # Ensure the date is in string format 'YYYY-MM-DD'
    date_str = date.strftime('%Y-%m-%d')

    query = {"symbol": symbol, "date": date_str}

    try:
        return pip_check_collection.find_one(query)
    except Exception as e:
        print(f"Error while checking data existence for {symbol} on {date_str}: {str(e)}")
        return None


# Function to load symbol data from MongoDB
def load_symbol_data(symbol):
    collection_name = "symbols_data"
    symbol_collection = db[collection_name]

    try:
        data = symbol_collection.find_one({"symbol": symbol})
        if data:
            # Convert string times back to datetime objects if necessary
            if 'start_price_time' in data and isinstance(data['start_price_time'], str):
                data['start_price_time'] = datetime.fromisoformat(data['start_price_time'])
            if 'last_update_time' in data and isinstance(data['last_update_time'], str):
                data['last_update_time'] = datetime.fromisoformat(data['last_update_time'])
            return data
        else:
            print(f"No data found for symbol {symbol}")
            return None
    except Exception as e:
        print(f"Error while loading data for {symbol}: {str(e)}")
        return None


# Function to save threshold symbols to MongoDB
def save_threshold_symbols_to_db(threshold_symbols):
    collection_name = "threshold_symbols"
    collection = db[collection_name]
    # Clear existing data
    collection.delete_many({})
    # Insert the updated threshold_symbols
    documents = []
    for symbol, data in threshold_symbols.items():
        data_to_insert = data.copy()
        data_to_insert['symbol'] = symbol
        # Convert datetime objects to strings for storage
        if 'threshold_time' in data_to_insert and isinstance(data_to_insert['threshold_time'], datetime):
            data_to_insert['threshold_time'] = data_to_insert['threshold_time'].isoformat()
        documents.append(data_to_insert)
    if documents:
        collection.insert_many(documents)

import random
import datetime

# In-memory storage to match JS version
sessions = {}
transactions = {}

def format_currency(amount):
    return f"Rs {amount:.2f}"

def generate_id():
    return "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=8))

def log_error(message):
    print("Error: " + message)
    tx_id = generate_id()
    transactions[tx_id] = {
        "type": "error",
        "message": message,
        "timestamp": datetime.datetime.now().isoformat()
    }

def is_valid_amount(amount):
    if not isinstance(amount, (int, float)):
        return False
    return amount > 0

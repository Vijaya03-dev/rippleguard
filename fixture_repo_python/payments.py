from .utils import format_currency, generate_id
from .auth import create_session

def process_payment(user_id, amount):
    session = create_session(user_id)
    transaction_id = generate_id()
    formatted = format_currency(amount)
    return {
        "transactionId": transaction_id,
        "formatted": formatted,
        "session": session
    }

def refund_payment(transaction_id):
    return transaction_id

import datetime
from .utils import generate_id

sessions = {}

def create_session(user_id):
    session_id = generate_id()
    session = {
        "sessionId": session_id,
        "userId": user_id,
        "createdAt": datetime.datetime.now().isoformat()
    }
    return session

def login(username, password):
    session = create_session(username)
    sessions[session["sessionId"]] = session
    return session

def logout_session(session_id):
    if session_id in sessions:
        del sessions[session_id]
    return session_id

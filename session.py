# session.py
import time
import uuid

class SessionManager:
    """
    مدير جلسات بسيط يحتفظ ببيانات مؤقتة لكل chat_id.
    يخزن: url, formats_map (short_id -> format_id), info, timestamp
    """

    def __init__(self, ttl_seconds=600):
        self.sessions = {}
        self.ttl = ttl_seconds

    def create(self, chat_id, data: dict):
        data_copy = data.copy()
        data_copy['created_at'] = time.time()
        self.sessions[chat_id] = data_copy

    def get(self, chat_id):
        s = self.sessions.get(chat_id)
        if not s:
            return None
        if time.time() - s.get('created_at', 0) > self.ttl:
            del self.sessions[chat_id]
            return None
        return s

    def set_field(self, chat_id, key, value):
        if chat_id in self.sessions:
            self.sessions[chat_id][key] = value

    def clear(self, chat_id):
        if chat_id in self.sessions:
            del self.sessions[chat_id]

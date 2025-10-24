import asyncio
from typing import Dict, Any
import json
from .ws_manager import send_to_user

class WsForwarder:
    def __init__(self, loop):
        self.loop = loop

    def schedule_send(self, user_id: int, data: dict):
        asyncio.run_coroutine_threadsafe(send_to_user(user_id, data), self.loop)
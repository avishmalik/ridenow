from fastapi import WebSocket
from typing import Dict

class WebsocketManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        print(f"🔗 User {user_id} connected")

    async def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            print(f"🔗 User {user_id} disconnected")

    async def send_personal_message(self, user_id: int, message: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)

    async def broadcast(self, message: str):
        for user_id, connection in self.active_connections.items():
            await connection.send_json(message)
        else:
            print(f"🔗 User {user_id} not found")

    # async def send_to_driver(self, driver_id: int, message: str):
    #     if driver_id in self.active_connections:
    #         await self.active_connections[driver_id].send_json(message)
    #     else:
    #         print(f"🔗 Driver {driver_id} not found")

    # async def send_to_user(self, user_id: int, message: str):
    #     if user_id in self.active_connections:
    #         await self.active_connections[user_id].send_json(message)
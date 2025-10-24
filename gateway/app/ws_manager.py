from fastapi import WebSocket
from typing import List, Dict
import threading
import redis
import os
from dotenv import load_dotenv
import json
import time

load_dotenv()

connections: Dict[int, List[WebSocket]] = {}
conn_lock = threading.Lock()

redis_client = redis.Redis(host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT", 6379), decode_responses=True)
CHANNEL = "ride_updates"

def add_connection(user_id: int, websocket: WebSocket):
    with conn_lock:
        lst = connections.get(user_id, [])
        if not lst:
            connections[user_id] = [websocket]
        else:
            lst.append(websocket)

def remove_connection(user_id: int, websocket: WebSocket):
    with conn_lock:
        lst = connections.get(user_id, [])
        if not lst:
            return
        try:
            lst.remove(websocket)
        except ValueError:
            pass
        if not lst:
            del connections[user_id]

async def send_to_user(user_id: int, message: dict):
    websockets = []
    with conn_lock:
        websockets = connections.get(user_id, [])
    
    for ws in websockets:
        try:
            ws.send_text(json.dumps(message))
        except Exception:
            pass

def redis_listener(app):
    pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(CHANNEL)

    while True:
        try:
            message = pubsub.get_message(timeout=1.0)
            if message and message.get('type') == 'message':
                payload = message.get('data')
                try:
                    data = json.loads(payload)
                except Exception:
                    continue
                user_id = data.get('user_id')
                driver_id = data.get("driver_id")

                loop = getattr(app, "loop", None)
                if loop:
                    if user_id:
                        loop.call_soon_threadsafe(lambda u=user_id, d=data: app.state.ws_forwarder.schedule_send(u, d))
                    if driver_id:
                        loop.call_soon_threadsafe(lambda u=driver_id, d=data: app.state.ws_forwarder.schedule_send(u, d))
        except Exception:
            print("Error in redis listener")
            time.sleep(2)

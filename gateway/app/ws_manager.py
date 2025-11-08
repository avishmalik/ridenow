from fastapi import WebSocket
from typing import List, Dict
import threading
import os
from dotenv import load_dotenv
import json
import time
import asyncio

load_dotenv()

# --- Thread-safe in-memory connection mapping ---
connections: Dict[int, List[WebSocket]] = {}
conn_lock = threading.Lock()

# --- Redis Setup (Optional) ---
redis_client = None
REDIS_AVAILABLE = False

try:
    import redis
    redis_host = os.getenv("REDIS_HOST")
    redis_port = os.getenv("REDIS_PORT")
    
    if redis_host and redis_port:
        redis_client = redis.Redis(
            host=redis_host,
            port=int(redis_port),
            decode_responses=True,
            socket_connect_timeout=2
        )
        # Test connection
        redis_client.ping()
        REDIS_AVAILABLE = True
        print("[WS] Redis connected and available")
    else:
        print("[WS] Redis not configured, using direct WebSocket broadcasting")
except Exception as e:
    print(f"[WS] Redis not available: {e}. Using direct WebSocket broadcasting only.")

CHANNEL = "ride_updates"


# --- Connection Management ---
def add_connection(user_id: int, websocket: WebSocket):
    with conn_lock:
        if user_id not in connections:
            connections[user_id] = []
        connections[user_id].append(websocket)
    print(f"[WS] User {user_id} connected. Total connections: {len(connections[user_id])}")


def remove_connection(user_id: int, websocket: WebSocket):
    with conn_lock:
        lst = connections.get(user_id, [])
        if websocket in lst:
            lst.remove(websocket)
            print(f"[WS] User {user_id} disconnected.")
            if not lst:
                del connections[user_id]


# --- Message Sending ---
async def send_to_user(user_id: int, message: dict):
    """Send a message to all WebSockets of a given user"""
    websockets = []
    with conn_lock:
        websockets = list(connections.get(user_id, []))

    for ws in websockets:
        try:
            await ws.send_text(json.dumps(message))
        except Exception as e:
            print(f"[WS] Error sending to user {user_id}: {e}")


async def broadcast(message: dict):
    """Send a message to all connected users"""
    with conn_lock:
        all_sockets = [ws for lst in connections.values() for ws in lst]

    print(f"[WS] Broadcasting to {len(all_sockets)} clients")

    for ws in all_sockets:
        try:
            await ws.send_text(json.dumps(message))
        except Exception as e:
            print(f"[WS] Broadcast error: {e}")


async def broadcast_to_drivers(message: dict):
    """Send a message to all connected drivers only"""
    from app.database import get_db
    from app.models import User
    
    # Get all driver user IDs from database
    db = next(get_db())
    try:
        drivers = db.query(User).filter(User.is_driver == True).all()
        driver_ids = [driver.id for driver in drivers]
        
        with conn_lock:
            driver_sockets = []
            for driver_id in driver_ids:
                if driver_id in connections:
                    driver_sockets.extend(connections[driver_id])
        
        print(f"[WS] Broadcasting to {len(driver_sockets)} driver connections")
        
        for ws in driver_sockets:
            try:
                await ws.send_text(json.dumps(message))
            except Exception as e:
                print(f"[WS] Error sending to driver: {e}")
    finally:
        db.close()


# --- Redis Listener (Optional) ---
def redis_listener(app):
    """Threaded Redis listener to push messages into event loop"""
    if not REDIS_AVAILABLE or not redis_client:
        print("[WS] Redis not available, skipping Redis listener")
        return
    
    try:
        pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
        pubsub.subscribe(CHANNEL)

        print("[WS] Redis listener started, waiting for ride updates...")

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
                    driver_id = data.get('driver_id')

                    loop = getattr(app, "loop", None) or getattr(app.state, "loop", None)
                    if loop:
                        # schedule sends asynchronously
                        if user_id:
                            loop.call_soon_threadsafe(
                                lambda u=user_id, d=data: asyncio.create_task(send_to_user(u, d))
                            )
                        if driver_id:
                            loop.call_soon_threadsafe(
                                lambda u=driver_id, d=data: asyncio.create_task(send_to_user(u, d))
                            )
                        # optional broadcast logic
                        if data.get("broadcast"):
                            loop.call_soon_threadsafe(
                                lambda d=data: asyncio.create_task(broadcast(d))
                            )
                        # broadcast to all drivers only
                        if data.get("broadcast_to_drivers"):
                            loop.call_soon_threadsafe(
                                lambda d=data: asyncio.create_task(broadcast_to_drivers(d))
                            )
            except Exception as e:
                print(f"[WS] Error in Redis listener: {e}")
                time.sleep(2)
    except Exception as e:
        print(f"[WS] Redis listener failed: {e}. Continuing without Redis.")


# --- Direct broadcast function (for use without Redis) ---
def broadcast_message_sync(message: dict, app=None):
    """Synchronous wrapper to broadcast messages directly via WebSocket"""
    if app and hasattr(app.state, "loop"):
        loop = app.state.loop
        if message.get("broadcast_to_drivers"):
            loop.call_soon_threadsafe(
                lambda d=message: asyncio.create_task(broadcast_to_drivers(d))
            )
        elif message.get("user_id"):
            loop.call_soon_threadsafe(
                lambda u=message.get("user_id"), d=message: asyncio.create_task(send_to_user(u, d))
            )
        elif message.get("broadcast"):
            loop.call_soon_threadsafe(
                lambda d=message: asyncio.create_task(broadcast(d))
            )

# ws_routes.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from .auth import decode_token_for_ws
from .database import get_db
from .models import Ride, User
from sqlalchemy.orm import Session
import json

router = APIRouter(prefix="/ws", tags=["WebSocket"])

active_connections = {}  # user_id -> WebSocket object


async def connect_user(user_id: int, websocket: WebSocket):
    await websocket.accept()
    active_connections[user_id] = websocket
    print(f"User {user_id} connected")


async def disconnect_user(user_id: int):
    active_connections.pop(user_id, None)
    print(f"User {user_id} disconnected")


async def send_message(user_id: int, message: dict):
    if user_id in active_connections:
        await active_connections[user_id].send_json(message)


@router.websocket("")
async def websocket_endpoint(websocket: WebSocket, token: str, db: Session = Depends(get_db)):
    user_data = decode_token_for_ws(token)
    user = db.query(User).filter(User.id == int(user_data["sub"])).first()

    if not user:
        await websocket.close(code=1008)
        return

    await connect_user(user.id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            # Rider requests a ride
            if action == "ride_requested":
                pickup = data["pickup"]
                dropoff = data["dropoff"]

                db_ride = Ride(user_id=user.id, pickup=pickup, dropoff=dropoff, status="requested")
                db.add(db_ride)
                db.commit()
                db.refresh(db_ride)

                # Notify all drivers
                for conn_user_id, conn_ws in active_connections.items():
                    conn_user = db.query(User).get(conn_user_id)
                    if conn_user and conn_user.is_driver:
                        await conn_ws.send_json({
                            "event": "new_ride",
                            "ride_id": db_ride.id,
                            "pickup": pickup,
                            "dropoff": dropoff,
                        })

            # Driver accepts a ride
            elif action == "ride_assigned":
                ride_id = data["ride_id"]
                db_ride = db.query(Ride).get(ride_id)
                if db_ride:
                    db_ride.driver_id = user.id
                    db_ride.status = "assigned"
                    db.commit()
                    db.refresh(db_ride)
                    await send_message(db_ride.user_id, {
                        "event": "ride_assigned",
                        "ride_id": db_ride.id,
                        "driver_id": user.id,
                    })

            # Driver completes ride
            elif action == "ride_completed":
                ride_id = data["ride_id"]
                db_ride = db.query(Ride).get(ride_id)
                if db_ride:
                    db_ride.status = "completed"
                    db.commit()
                    await send_message(db_ride.user_id, {
                        "event": "ride_completed",
                        "ride_id": db_ride.id,
                    })

    except WebSocketDisconnect:
        await disconnect_user(user.id)

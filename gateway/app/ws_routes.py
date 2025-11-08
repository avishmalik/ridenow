# ws_routes.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from .auth import decode_token_for_ws
from .database import get_db
from .models import Ride, User
from .ws_manager import add_connection, remove_connection
from sqlalchemy.orm import Session
import json

router = APIRouter(prefix="/ws", tags=["WebSocket"])

active_connections = {}  # user_id -> WebSocket object (kept for backward compatibility)


async def connect_user(user_id: int, websocket: WebSocket):
    await websocket.accept()
    active_connections[user_id] = websocket
    # Also register in ws_manager for Redis pub/sub broadcasting
    add_connection(user_id, websocket)
    print(f"User {user_id} connected")


async def disconnect_user(user_id: int):
    websocket = active_connections.pop(user_id, None)
    if websocket:
        # Also unregister from ws_manager
        remove_connection(user_id, websocket)
    print(f"User {user_id} disconnected")


async def send_message(user_id: int, message: dict):
    if user_id in active_connections:
        await active_connections[user_id].send_json(message)


async def broadcast_to_drivers(message: dict, db: Session):
    """Broadcast message to all connected drivers"""
    driver_connections = []
    for conn_user_id, conn_ws in active_connections.items():
        conn_user = db.query(User).filter(User.id == conn_user_id).first()
        if conn_user and conn_user.is_driver:
            driver_connections.append(conn_ws)
    
    print(f"[WS] Broadcasting to {len(driver_connections)} driver connections")
    for ws in driver_connections:
        try:
            await ws.send_json(message)
        except Exception as e:
            print(f"[WS] Error sending to driver: {e}")


@router.websocket("")
async def websocket_endpoint(websocket: WebSocket, token: str, db: Session = Depends(get_db)):
    try:
        user_data = decode_token_for_ws(token)
        user = db.query(User).filter(User.id == int(user_data["sub"])).first()

        if not user:
            await websocket.close(code=1008, reason="User not found")
            return

        await connect_user(user.id, websocket)
        
        # Send welcome message
        await websocket.send_json({
            "event": "connected",
            "message": "WebSocket connection established",
            "user_id": user.id,
            "is_driver": user.is_driver
        })
        
        while True:
            try:
                # Wait for message with timeout handling
                data = await websocket.receive_json()
                action = data.get("action") or data.get("event")  # Support both formats
                print(f"Received action: {action}")
                
                # Handle empty messages or ping/pong
                if not action or action == "ping":
                    await websocket.send_json({"event": "pong"})
                    continue
                
                # Handle ride_requested or ride_request (support both formats)
                if action == "ride_requested" or action == "ride_request":
                    pickup = data.get("pickup") or (data.get("payload") and data["payload"].get("pickup"))
                    dropoff = data.get("dropoff") or (data.get("payload") and data["payload"].get("dropoff"))
                    
                    if not pickup or not dropoff:
                        await websocket.send_json({
                            "event": "error",
                            "message": "Missing pickup or dropoff location"
                        })
                        continue
                    
                    print(f"Creating ride: {pickup} -> {dropoff}")
                    db_ride = Ride(user_id=user.id, pickup=pickup, dropoff=dropoff, status="requested")
                    db.add(db_ride)
                    db.commit()
                    db.refresh(db_ride)
                    print(f"Ride created: {db_ride.id}")
                    
                    # Notify all drivers
                    driver_count = 0
                    for conn_user_id, conn_ws in active_connections.items():
                        conn_user = db.query(User).filter(User.id == conn_user_id).first()
                        if conn_user and conn_user.is_driver:
                            try:
                                await conn_ws.send_json({
                                    "event": "new_ride",
                                    "ride_id": db_ride.id,
                                    "pickup": pickup,
                                    "dropoff": dropoff,
                                    "user_id": user.id
                                })
                                driver_count += 1
                            except Exception as e:
                                print(f"Error sending to driver {conn_user_id}: {e}")
                    
                    await websocket.send_json({
                        "event": "ride_created",
                        "ride_id": db_ride.id,
                        "message": f"Ride created and notified {driver_count} drivers"
                    })
                    print(f'Notified {driver_count} driver connections')
                
                # Driver accepts a ride
                elif action == "ride_assigned" or action == "ride_accept":
                    if not user.is_driver:
                        await websocket.send_json({
                            "event": "error",
                            "message": "Only drivers can assign rides"
                        })
                        continue
                    ride_id = data.get("ride_id") or (data.get("payload") and data["payload"].get("ride_id"))
                    if not ride_id:
                        await websocket.send_json({
                            "event": "error",
                            "message": "Missing ride_id"
                        })
                        continue
                    
                    db_ride = db.query(Ride).filter(Ride.id == ride_id).first()
                    if db_ride:
                        if not db_ride:
                            await websocket.send_json({
                                "event": "error",
                                "message": "Ride not found"
                            })
                            continue
                        if db_ride.status != "requested":
                            await websocket.send_json({
                                "event": "error",
                                "message": "Ride already assigned or completed"
                            })
                            continue
                        db_ride.driver_id = user.id
                        db_ride.status = "assigned"
                        db.commit()
                        db.refresh(db_ride)
                        await send_message(db_ride.user_id, {
                            "event": "ride_assigned",
                            "ride_id": db_ride.id,
                            "driver_id": user.id,
                        })
                        await websocket.send_json({
                            "event": "ride_assigned_success",
                            "ride_id": db_ride.id
                        })
                    else:
                        await websocket.send_json({
                            "event": "error",
                            "message": "Ride not found"
                        })

                # Driver completes ride
                elif action == "ride_completed" or action == "ride_complete":
                    if not user.is_driver:
                        await websocket.send_json({
                            "event": "error",
                            "message": "Only drivers can assign rides"
                        })
                        continue
                    ride_id = data.get("ride_id") or (data.get("payload") and data["payload"].get("ride_id"))
                    if not ride_id:
                        await websocket.send_json({
                            "event": "error",
                            "message": "Missing ride_id"
                        })
                        continue
                    
                    db_ride = db.query(Ride).filter(Ride.id == ride_id).first()
                    if db_ride:
                        if not db_ride:
                            await websocket.send_json({
                                "event": "error",
                                "message": "Ride not found"
                            })
                            continue

                        if db_ride.status != "assigned":
                            await websocket.send_json({
                                "event": "error",
                                "message": "Ride not assigned to driver"
                            })
                            continue
                        db_ride.status = "completed"
                        db.commit()
                        await send_message(db_ride.user_id, {
                            "event": "ride_completed",
                            "ride_id": db_ride.id,
                        })
                        await websocket.send_json({
                            "event": "ride_completed_success",
                            "ride_id": db_ride.id
                        })
                    else:
                        await websocket.send_json({
                            "event": "error",
                            "message": "Ride not found"
                        })
                else:
                    await websocket.send_json({
                        "event": "error",
                        "message": f"Unknown action: {action}"
                    })
                    
            except Exception as e:
                print(f"Error processing message: {e}")
                await websocket.send_json({
                    "event": "error",
                    "message": str(e)
                })

    except WebSocketDisconnect:
        print(f"WebSocket disconnected for user {user.id}")
        await disconnect_user(user.id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        await disconnect_user(user.id)

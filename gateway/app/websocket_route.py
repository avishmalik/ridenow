from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from .auth import decode_token_for_ws
from .ws_manager import add_connection, remove_connection, send_to_user, broadcast
import json

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = None):
    """
    WebSocket endpoint for both riders and drivers.
    Supports real-time ride request, assignment, and updates.
    """
    if not token:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    try:
        payload = decode_token_for_ws(token)
        user_id = int(payload.get("sub"))
    except Exception:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()
    add_connection(user_id, websocket)
    print(f"✅ WebSocket connected: user {user_id}")

    try:
        while True:
            msg = await websocket.receive_text()

            try:
                data = json.loads(msg)
            except json.JSONDecodeError:
                await websocket.send_text("❌ Invalid message format")
                continue

            event = data.get("event")
            payload = data.get("payload", {})

            # 🚕 Handle ride request event
            if event == "ride_request":
                await broadcast({
                    "event": "new_ride",
                    "payload": {"rider_id": user_id, **payload}
                })
                await websocket.send_json({"event": "ride_requested", "payload": payload})

            # ✅ Handle driver accepting ride
            elif event == "ride_accept":
                rider_id = payload.get("rider_id")
                ride_id = payload.get("ride_id")
                await send_to_user(rider_id, {
                    "event": "ride_accepted",
                    "payload": {"driver_id": user_id, "ride_id": ride_id}
                })
                await websocket.send_json({"event": "ride_assigned", "payload": {"ride_id": ride_id}})

            # 🏁 Handle ride completion
            elif event == "ride_complete":
                rider_id = payload.get("rider_id")
                ride_id = payload.get("ride_id")
                await send_to_user(rider_id, {
                    "event": "ride_completed",
                    "payload": {"ride_id": ride_id, "driver_id": user_id}
                })
                await websocket.send_json({"event": "ride_complete_ack", "payload": {"ride_id": ride_id}})

            # ❌ Cancel ride
            elif event == "ride_cancel":
                await broadcast({
                    "event": "ride_cancelled",
                    "payload": {"user_id": user_id, **payload}
                })

            # 🔁 Echo or unknown event
            else:
                await websocket.send_json({
                    "event": "echo",
                    "payload": {"received": data}
                })

    except WebSocketDisconnect:
        print(f"❌ WebSocket disconnected: user {user_id}")
        remove_connection(user_id, websocket)
    except Exception as e:
        print(f"⚠️ WebSocket error: {e}")
        remove_connection(user_id, websocket)
        try:
            await websocket.close()
        except Exception:
            pass

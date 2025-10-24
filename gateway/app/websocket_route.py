from fastapi import WebSocket, Depends, WebSocketDisconnect, APIRouter
from .auth import decode_token_for_ws
from .ws_manager import add_connection, remove_connection

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = None):
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


    try:
        while True:
            msg = await websocket.receive_text()

            await websocket.send_text(msg)
    except WebSocketDisconnect:
        remove_connection(user_id, websocket)
    except Exception:
        remove_connection(user_id, websocket)
        try:
            await websocket.close()
        except Exception:
            pass
        

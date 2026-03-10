from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.services.websocket_manager import manager
from app.database.session import get_db
from sqlalchemy.orm import Session
from app.models.user import User
from app.auth.dependencies import get_current_user
from fastapi.security import OAuth2PasswordBearer

router = APIRouter()

@router.websocket("/ws/chat/{company_id}")
async def websocket_chat(
    websocket: WebSocket, 
    company_id: int
):
    """
    WebSocket endpoint for real-time chat updates.
    """
    print(f"[WS_ROUTER] Handshake initiated for Company {company_id}")
    try:
        await manager.connect(websocket, company_id)
        print(f"[WS_ROUTER] Connection established and accepted for Company {company_id}")
        
        while True:
            # Keep the connection open and wait for messages (though we primarily broadcast)
            data = await websocket.receive_text()
            print(f"[WS_ROUTER] Received heart-beat/data: {data}")
            
    except WebSocketDisconnect:
        print(f"[WS_ROUTER] Client disconnected (normal/clean) for Company {company_id}")
        manager.disconnect(websocket, company_id)
    except Exception as e:
        print(f"[WS_ROUTER] WebSocket error for Company {company_id}: {e}")
        manager.disconnect(websocket, company_id)

from typing import Dict, List
from fastapi import WebSocket
import json

class ConnectionManager:
    def __init__(self):
        # Maps company_id -> list of active WebSockets
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, company_id: int):
        await websocket.accept()
        if company_id not in self.active_connections:
            self.active_connections[company_id] = []
        self.active_connections[company_id].append(websocket)
        print(f"WebSocket connected for Company {company_id}")

    def disconnect(self, websocket: WebSocket, company_id: int):
        if company_id in self.active_connections:
            self.active_connections[company_id].remove(websocket)
            if not self.active_connections[company_id]:
                del self.active_connections[company_id]
        print(f"WebSocket disconnected for Company {company_id}")

    async def broadcast(self, company_id: int, message: dict):
        """
        Sends a message to all connected clients for a specific company.
        """
        connections = self.active_connections.get(company_id, [])
        print(f"[WS_MANAGER] Broadcasting to {len(connections)} clients for Company {company_id}. Event: {message.get('event')}")
        
        if connections:
            for connection in connections:
                try:
                    await connection.send_json(message)
                    print(f"[WS_MANAGER] Sent successfully to connection.")
                except Exception as e:
                    print(f"[WS_MANAGER] Error sending WebSocket message: {e}")

manager = ConnectionManager()

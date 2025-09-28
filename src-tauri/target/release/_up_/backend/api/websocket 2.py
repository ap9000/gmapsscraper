from __future__ import annotations

import json
import asyncio
from typing import List, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect


class WebSocketManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"✅ WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"❌ WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send message to specific WebSocket."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            print(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Send message to all connected WebSockets."""
        if not self.active_connections:
            return
            
        # Create list of tasks for concurrent sending
        tasks = []
        for connection in self.active_connections.copy():  # Copy to avoid modification during iteration
            try:
                tasks.append(connection.send_text(json.dumps(message)))
            except Exception as e:
                print(f"Error preparing broadcast to connection: {e}")
                self.disconnect(connection)
        
        # Send all messages concurrently
        if tasks:
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except Exception as e:
                print(f"Error in broadcast: {e}")
    
    def emit_search_progress(self, job_id: str, progress: int, status: str, details: str = ""):
        """Emit search progress update."""
        message = {
            "type": "search.progress",
            "data": {
                "job_id": job_id,
                "progress": progress,
                "status": status,
                "details": details,
                "timestamp": asyncio.get_event_loop().time()
            }
        }
        # Create task for background execution
        asyncio.create_task(self.broadcast(message))
    
    def emit_enrichment_status(self, job_id: str, processed: int, total: int, found_emails: int):
        """Emit enrichment progress update."""
        message = {
            "type": "enrichment.status",
            "data": {
                "job_id": job_id,
                "processed": processed,
                "total": total,
                "found_emails": found_emails,
                "timestamp": asyncio.get_event_loop().time()
            }
        }
        asyncio.create_task(self.broadcast(message))
    
    def emit_export_complete(self, job_id: str, format_type: str, file_path: str):
        """Emit export completion notification."""
        message = {
            "type": "export.complete",
            "data": {
                "job_id": job_id,
                "format": format_type,
                "file_path": file_path,
                "timestamp": asyncio.get_event_loop().time()
            }
        }
        asyncio.create_task(self.broadcast(message))
    
    def emit_error(self, job_id: str, error: str, error_type: str = "general"):
        """Emit error notification."""
        message = {
            "type": "error",
            "data": {
                "job_id": job_id,
                "error": error,
                "error_type": error_type,
                "timestamp": asyncio.get_event_loop().time()
            }
        }
        asyncio.create_task(self.broadcast(message))


# Global WebSocket manager instance
websocket_manager = WebSocketManager()


async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication."""
    await websocket_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                # Handle ping/pong for connection health
                if message.get("type") == "ping":
                    await websocket_manager.send_personal_message(
                        {"type": "pong", "timestamp": asyncio.get_event_loop().time()},
                        websocket
                    )
            except json.JSONDecodeError:
                await websocket_manager.send_personal_message(
                    {"type": "error", "data": {"error": "Invalid JSON message"}},
                    websocket
                )
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
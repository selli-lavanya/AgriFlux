import asyncio
import json
from typing import Dict, Set, Any
import datetime

class NotificationManager:
    def __init__(self):
        # We store connections grouped by user_id and then role-based subscriptions
        # For simplicity, we just use a flat list of active queue per connection.
        # { user_id: [Queue, Queue] }
        self.active_connections: Dict[int, list[asyncio.Queue]] = {}
        # Admin broadcasts
        self.admin_queues: list[asyncio.Queue] = []

    async def subscribe(self, user_id: int, role: str) -> asyncio.Queue:
        queue = asyncio.Queue()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(queue)
        
        if role == 'admin':
            self.admin_queues.append(queue)
            
        return queue

    def unsubscribe(self, queue: asyncio.Queue, user_id: int, role: str):
        if user_id in self.active_connections:
            if queue in self.active_connections[user_id]:
                self.active_connections[user_id].remove(queue)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                
        if role == 'admin' and queue in self.admin_queues:
            self.admin_queues.remove(queue)

    def _build_payload(self, event_type: str, entity_type: str, entity_id: int, message: str) -> str:
        data = {
            "event_type": event_type,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "message": message,
            "timestamp": datetime.datetime.now().isoformat()
        }
        return json.dumps(data)

    async def notify_user(self, target_user_id: int, event_type: str, entity_type: str, entity_id: int, message: str):
        if target_user_id in self.active_connections:
            payload = self._build_payload(event_type, entity_type, entity_id, message)
            for queue in self.active_connections[target_user_id]:
                await queue.put(payload)

    async def notify_admins(self, event_type: str, entity_type: str, entity_id: int, message: str):
        payload = self._build_payload(event_type, entity_type, entity_id, message)
        for queue in self.admin_queues:
            await queue.put(payload)

notification_manager = NotificationManager()

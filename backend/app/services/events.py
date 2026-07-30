import json
from fastapi import WebSocket


class EventBroker:
    def __init__(self) -> None: self.connections: set[WebSocket] = set()
    async def connect(self, socket: WebSocket) -> None: await socket.accept(); self.connections.add(socket)
    def disconnect(self, socket: WebSocket) -> None: self.connections.discard(socket)
    async def publish(self, event: str, payload: dict) -> None:
        message = json.dumps({"event": event, "payload": payload}, default=str)
        for socket in list(self.connections):
            try: await socket.send_text(message)
            except Exception: self.disconnect(socket)


broker = EventBroker()

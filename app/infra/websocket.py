from fastapi import WebSocket
from typing import List,Set
websocket_connections: Set[WebSocket] = set()
websocket_connections_admin:Set[WebSocket]=set()

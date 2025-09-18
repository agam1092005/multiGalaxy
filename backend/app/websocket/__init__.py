"""
WebSocket module for real-time communication
"""
from .manager import connection_manager, ConnectionManager, MessageType

__all__ = ['connection_manager', 'ConnectionManager', 'MessageType']
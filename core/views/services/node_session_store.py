"""
Node Session Store Module
Manages stateful node instances across multiple executions.
"""

import threading
import time
from typing import Any, Dict, Optional, Tuple


def _composite_key(session_id: str, instance_key: str) -> str:
    """Build store key from session_id and instance_key (e.g. workflow node id or node type identifier)."""
    return f"{session_id}:{instance_key}"


class NodeSessionStore:
    """
    In-memory store for node instances keyed by (session_id, instance_key).
    
    Enables stateful node execution by reusing the same instance per (session, node).
    Each workflow node or node type gets its own instance within a session.
    
    Features:
    - Thread-safe singleton pattern
    - 30-minute TTL auto-cleanup for unused entries
    """
    
    _instance = None
    _lock = threading.Lock()
    
    # Entries unused for 30 minutes are automatically cleaned up
    TTL_SECONDS = 30 * 60  # 30 minutes
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    # Store: {composite_key: (instance, last_accessed_timestamp)}
                    cls._instance._sessions: Dict[str, Tuple[Any, float]] = {}
                    cls._instance._session_lock = threading.Lock()
        return cls._instance
    
    def _cleanup_expired(self) -> int:
        """
        Remove entries that haven't been accessed within TTL.
        Called internally on each get/set operation (lazy cleanup).
        
        Returns:
            Number of entries cleaned up
        """
        now = time.time()
        expired = [
            key
            for key, (_, last_accessed) in self._sessions.items()
            if now - last_accessed > self.TTL_SECONDS
        ]
        for key in expired:
            del self._sessions[key]
        return len(expired)
    
    def get(self, session_id: str, instance_key: str) -> Optional[Any]:
        """
        Get a node instance by session_id and instance_key.
        Updates the last accessed timestamp.
        
        Args:
            session_id: Session identifier
            instance_key: Node identity (e.g. workflow node UUID or node type identifier)
            
        Returns:
            Node instance if exists, None otherwise
        """
        with self._session_lock:
            self._cleanup_expired()
            key = _composite_key(session_id, instance_key)
            if key in self._sessions:
                instance, _ = self._sessions[key]
                self._sessions[key] = (instance, time.time())
                return instance
            return None
    
    def set(self, session_id: str, instance_key: str, instance: Any) -> None:
        """
        Store a node instance for (session_id, instance_key).
        
        Args:
            session_id: Session identifier
            instance_key: Node identity (e.g. workflow node UUID or node type identifier)
            instance: Node instance to store
        """
        with self._session_lock:
            self._cleanup_expired()
            key = _composite_key(session_id, instance_key)
            self._sessions[key] = (instance, time.time())
    
    def clear_session(self, session_id: str) -> int:
        """
        Clear all node instances for this session_id.
        Used on timeout and for reset-session API.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Number of entries removed
        """
        with self._session_lock:
            self._cleanup_expired()
            prefix = session_id + ":"
            to_remove = [key for key in self._sessions if key.startswith(prefix)]
            for key in to_remove:
                del self._sessions[key]
            return len(to_remove)
    
    def clear_all(self) -> int:
        """
        Clear all sessions.
        
        Returns:
            Number of sessions cleared
        """
        with self._session_lock:
            count = len(self._sessions)
            self._sessions.clear()
            return count
    
    def get_session_count(self) -> int:
        """
        Get the number of active sessions.
        
        Returns:
            Number of active sessions
        """
        with self._session_lock:
            self._cleanup_expired()
            return len(self._sessions)

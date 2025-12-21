"""
Node Session Store Module
Manages stateful node instances across multiple executions.
"""

import threading
import time
from typing import Any, Dict, Optional, Tuple


class NodeSessionStore:
    """
    In-memory store for node instances keyed by session_id.
    
    Enables stateful node execution by reusing the same instance
    across multiple execute calls within a session.
    
    Features:
    - Thread-safe singleton pattern
    - 30-minute TTL auto-cleanup for unused sessions
    """
    
    _instance = None
    _lock = threading.Lock()
    
    # Sessions unused for 30 minutes are automatically cleaned up
    TTL_SECONDS = 30 * 60  # 30 minutes
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    # Store: {session_id: (instance, last_accessed_timestamp)}
                    cls._instance._sessions: Dict[str, Tuple[Any, float]] = {}
                    cls._instance._session_lock = threading.Lock()
        return cls._instance
    
    def _cleanup_expired(self) -> int:
        """
        Remove sessions that haven't been accessed within TTL.
        Called internally on each get/set operation (lazy cleanup).
        
        Returns:
            Number of sessions cleaned up
        """
        now = time.time()
        expired = [
            session_id 
            for session_id, (_, last_accessed) in self._sessions.items()
            if now - last_accessed > self.TTL_SECONDS
        ]
        for session_id in expired:
            del self._sessions[session_id]
        return len(expired)
    
    def get(self, session_id: str) -> Optional[Any]:
        """
        Get a node instance by session_id.
        Updates the last accessed timestamp.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Node instance if exists, None otherwise
        """
        with self._session_lock:
            self._cleanup_expired()
            
            if session_id in self._sessions:
                instance, _ = self._sessions[session_id]
                # Update last accessed time
                self._sessions[session_id] = (instance, time.time())
                return instance
            return None
    
    def set(self, session_id: str, instance: Any) -> None:
        """
        Store a node instance for a session.
        
        Args:
            session_id: Unique session identifier
            instance: Node instance to store
        """
        with self._session_lock:
            self._cleanup_expired()
            self._sessions[session_id] = (instance, time.time())
    
    def clear(self, session_id: str) -> bool:
        """
        Clear a session and its node instance.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            True if session existed and was cleared, False otherwise
        """
        with self._session_lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False
    
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

"""
Redis Execution State Store

Stores workflow execution state in Redis for cross-process access.
Enables state sharing between Celery workers and Daphne WebSocket consumers.
"""

import json
import redis
import structlog
from datetime import datetime
from typing import Dict, Any, Optional

logger = structlog.get_logger(__name__)

# Redis connection
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """Get or create Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True
        )
    return _redis_client


class RedisExecutionStateStore:
    """
    Stores workflow execution state in Redis for cross-process access.
    
    Redis Key Structure:
        workflow_execution:{workflow_id} -> JSON state object
        
    State Structure:
        {
            "workflow_id": "uuid",
            "status": "running",
            "started_at": "ISO timestamp",
            "executing_nodes": {
                "node_id": {"node_type": "...", "started_at": "..."}
            },
            "completed_nodes": [...],
            "completed_count": 0,
            "total_nodes": 10
        }
    """
    
    KEY_PREFIX = "workflow_execution:"
    TTL_SECONDS = 3600  # 1 hour auto-cleanup
    
    def __init__(self):
        self._redis = get_redis_client()
    
    def _get_key(self, workflow_id: str) -> str:
        """Generate Redis key for workflow."""
        return f"{self.KEY_PREFIX}{workflow_id}"
    
    def start_workflow(
        self, 
        workflow_id: str, 
        total_nodes: int = 0
    ) -> None:
        """
        Initialize workflow execution state in Redis.
        
        Args:
            workflow_id: The workflow ID
            total_nodes: Total number of nodes in the workflow
        """
        state = {
            "workflow_id": workflow_id,
            "status": "running",
            "started_at": datetime.utcnow().isoformat() + "Z",
            "executing_nodes": {},
            "completed_nodes": [],
            "completed_count": 0,
            "total_nodes": total_nodes,
        }
        
        key = self._get_key(workflow_id)
        self._redis.set(key, json.dumps(state), ex=self.TTL_SECONDS)
        
        logger.info("Workflow state initialized in Redis", workflow_id=workflow_id)
    
    def get_state(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current execution state from Redis.
        
        Args:
            workflow_id: The workflow ID
            
        Returns:
            State dict or None if not found
        """
        key = self._get_key(workflow_id)
        data = self._redis.get(key)
        
        if data:
            state = json.loads(data)
            
            # Calculate current durations for executing nodes
            now = datetime.utcnow()
            for node_id, node_info in state.get("executing_nodes", {}).items():
                if "started_at" in node_info:
                    try:
                        started = datetime.fromisoformat(node_info["started_at"].rstrip("Z"))
                        node_info["duration_seconds"] = (now - started).total_seconds()
                    except (ValueError, TypeError):
                        node_info["duration_seconds"] = 0
            
            return state
        
        return None
    
    def update_node_started(
        self, 
        workflow_id: str, 
        node_id: str, 
        node_type: str
    ) -> None:
        """
        Add a node to executing_nodes.
        
        Args:
            workflow_id: The workflow ID
            node_id: The node instance ID
            node_type: The node type identifier
        """
        key = self._get_key(workflow_id)
        data = self._redis.get(key)
        
        if not data:
            logger.warning("No state found for workflow", workflow_id=workflow_id)
            return
        
        state = json.loads(data)
        state["executing_nodes"][node_id] = {
            "node_type": node_type,
            "started_at": datetime.utcnow().isoformat() + "Z",
        }
        
        self._redis.set(key, json.dumps(state), ex=self.TTL_SECONDS)
        
        logger.debug(
            "Node started in Redis state",
            workflow_id=workflow_id,
            node_id=node_id,
            node_type=node_type
        )
    
    def update_node_completed(
        self, 
        workflow_id: str, 
        node_id: str,
        node_type: str,
        route: Optional[str] = None
    ) -> float:
        """
        Move a node from executing to completed.
        
        Args:
            workflow_id: The workflow ID
            node_id: The node instance ID
            node_type: The node type identifier
            route: Optional route taken (for conditional nodes)
            
        Returns:
            Duration in seconds
        """
        key = self._get_key(workflow_id)
        data = self._redis.get(key)
        
        if not data:
            logger.warning("No state found for workflow", workflow_id=workflow_id)
            return 0.0
        
        state = json.loads(data)
        completed_at = datetime.utcnow()
        duration = 0.0
        
        # Calculate duration if node was in executing_nodes
        if node_id in state["executing_nodes"]:
            node_info = state["executing_nodes"].pop(node_id)
            try:
                started = datetime.fromisoformat(node_info["started_at"].rstrip("Z"))
                duration = (completed_at - started).total_seconds()
            except (ValueError, TypeError, KeyError):
                duration = 0.0
        
        # Add to completed nodes
        completed_entry = {
            "node_id": node_id,
            "node_type": node_type,
            "completed_at": completed_at.isoformat() + "Z",
            "duration_seconds": duration,
        }
        if route:
            completed_entry["route"] = route
        
        state["completed_nodes"].append(completed_entry)
        state["completed_count"] = len(state["completed_nodes"])
        
        self._redis.set(key, json.dumps(state), ex=self.TTL_SECONDS)
        
        logger.debug(
            "Node completed in Redis state",
            workflow_id=workflow_id,
            node_id=node_id,
            duration=duration,
            route=route
        )
        
        return duration
    
    def update_node_failed(
        self, 
        workflow_id: str, 
        node_id: str,
        node_type: str,
        error: str
    ) -> None:
        """
        Record a node failure.
        
        Args:
            workflow_id: The workflow ID
            node_id: The node instance ID
            node_type: The node type identifier
            error: Error message
        """
        key = self._get_key(workflow_id)
        data = self._redis.get(key)
        
        if not data:
            return
        
        state = json.loads(data)
        
        # Remove from executing if present
        state["executing_nodes"].pop(node_id, None)
        
        self._redis.set(key, json.dumps(state), ex=self.TTL_SECONDS)
        
        logger.debug(
            "Node failed in Redis state",
            workflow_id=workflow_id,
            node_id=node_id,
            error=error
        )
    
    def complete_workflow(
        self, 
        workflow_id: str, 
        status: str = "completed"
    ) -> None:
        """
        Mark workflow as completed.
        
        Args:
            workflow_id: The workflow ID
            status: Final status ("completed" or "failed")
        """
        key = self._get_key(workflow_id)
        data = self._redis.get(key)
        
        if not data:
            return
        
        state = json.loads(data)
        state["status"] = status
        state["completed_at"] = datetime.utcnow().isoformat() + "Z"
        
        # Calculate total duration
        if "started_at" in state:
            try:
                started = datetime.fromisoformat(state["started_at"].rstrip("Z"))
                state["total_duration_seconds"] = (
                    datetime.utcnow() - started
                ).total_seconds()
            except (ValueError, TypeError):
                pass
        
        # Clear executing nodes
        state["executing_nodes"] = {}
        
        self._redis.set(key, json.dumps(state), ex=self.TTL_SECONDS)
        
        logger.info(
            "Workflow completed in Redis state",
            workflow_id=workflow_id,
            status=status
        )
    
    def fail_workflow(self, workflow_id: str, error: str) -> None:
        """
        Mark workflow as failed.
        
        Args:
            workflow_id: The workflow ID
            error: Error message
        """
        key = self._get_key(workflow_id)
        data = self._redis.get(key)
        
        if data:
            state = json.loads(data)
            state["status"] = "failed"
            state["error"] = error
            state["completed_at"] = datetime.utcnow().isoformat() + "Z"
            state["executing_nodes"] = {}
            
            self._redis.set(key, json.dumps(state), ex=self.TTL_SECONDS)
        
        logger.error(
            "Workflow failed in Redis state",
            workflow_id=workflow_id,
            error=error
        )
    
    def delete_state(self, workflow_id: str) -> None:
        """
        Remove state from Redis (manual cleanup).
        
        Args:
            workflow_id: The workflow ID
        """
        key = self._get_key(workflow_id)
        self._redis.delete(key)
        
        logger.debug("Workflow state deleted from Redis", workflow_id=workflow_id)


# Global singleton instance
redis_state_store = RedisExecutionStateStore()


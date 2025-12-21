"""
Execution State Tracker

Tracks the real-time execution state of a workflow, including which nodes are
currently executing, their durations, and completed nodes. Thread-safe for
parallel execution across multiple flow runners.
"""

from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Dict, List, Any, Optional
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class NodeExecutionInfo:
    """Information about a currently executing node."""
    node_id: str
    node_type: str
    started_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict with duration calculation."""
        now = datetime.utcnow()
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "started_at": self.started_at.isoformat() + "Z",
            "duration_seconds": (now - self.started_at).total_seconds(),
        }


@dataclass
class CompletedNodeInfo:
    """Information about a completed node."""
    node_id: str
    node_type: str
    completed_at: datetime
    duration_seconds: float
    route: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict."""
        result = {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "completed_at": self.completed_at.isoformat() + "Z",
            "duration_seconds": self.duration_seconds,
        }
        if self.route:
            result["route"] = self.route
        return result


class ExecutionStateTracker:
    """
    Tracks real-time execution state for a workflow.
    
    Thread-safe for parallel execution across multiple flow runners.
    Provides full state snapshot for WebSocket reconnection.
    """
    
    # Status constants
    STATUS_IDLE = "idle"
    STATUS_RUNNING = "running"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    
    def __init__(self, workflow_id: str, total_nodes: int = 0):
        """
        Initialize the state tracker.
        
        Args:
            workflow_id: The workflow ID
            total_nodes: Total number of nodes in the workflow (for progress)
        """
        self.workflow_id = workflow_id
        self.total_nodes = total_nodes
        self._lock = Lock()
        
        # State
        self._status: str = self.STATUS_IDLE
        self._started_at: Optional[datetime] = None
        self._completed_at: Optional[datetime] = None
        self._executing_nodes: Dict[str, NodeExecutionInfo] = {}
        self._completed_nodes: List[CompletedNodeInfo] = []
        self._error: Optional[str] = None
        self._active_runners: int = 0
    
    def start_workflow(self) -> None:
        """Mark workflow as started."""
        with self._lock:
            self._status = self.STATUS_RUNNING
            self._started_at = datetime.utcnow()
            self._completed_at = None
            self._executing_nodes.clear()
            self._completed_nodes.clear()
            self._error = None
            logger.info("Workflow execution started", workflow_id=self.workflow_id)
    
    def register_runner(self) -> None:
        """Register an active flow runner."""
        with self._lock:
            self._active_runners += 1
    
    def unregister_runner(self) -> None:
        """Unregister a flow runner. Marks workflow complete when all runners finish."""
        with self._lock:
            self._active_runners -= 1
            if self._active_runners <= 0 and self._status == self.STATUS_RUNNING:
                self._status = self.STATUS_COMPLETED
                self._completed_at = datetime.utcnow()
                logger.info("Workflow execution completed", workflow_id=self.workflow_id)
    
    def on_node_started(self, node_id: str, node_type: str) -> None:
        """
        Record that a node has started executing.
        
        Args:
            node_id: The node instance ID
            node_type: The node type identifier
        """
        with self._lock:
            self._executing_nodes[node_id] = NodeExecutionInfo(
                node_id=node_id,
                node_type=node_type,
                started_at=datetime.utcnow(),
            )
            logger.debug(
                "Node started",
                node_id=node_id,
                node_type=node_type,
                workflow_id=self.workflow_id
            )
    
    def on_node_completed(
        self, 
        node_id: str, 
        node_type: str,
        route: Optional[str] = None
    ) -> float:
        """
        Record that a node has completed executing.
        
        Args:
            node_id: The node instance ID
            node_type: The node type identifier
            route: Optional route taken (for conditional nodes)
            
        Returns:
            Duration in seconds
        """
        with self._lock:
            completed_at = datetime.utcnow()
            duration = 0.0
            
            # Calculate duration if we have start time
            if node_id in self._executing_nodes:
                start_info = self._executing_nodes.pop(node_id)
                duration = (completed_at - start_info.started_at).total_seconds()
            
            self._completed_nodes.append(CompletedNodeInfo(
                node_id=node_id,
                node_type=node_type,
                completed_at=completed_at,
                duration_seconds=duration,
                route=route,
            ))
            
            logger.debug(
                "Node completed",
                node_id=node_id,
                node_type=node_type,
                duration=duration,
                route=route,
                workflow_id=self.workflow_id
            )
            
            return duration
    
    def on_node_failed(self, node_id: str, node_type: str, error: str) -> None:
        """
        Record that a node has failed.
        
        Args:
            node_id: The node instance ID
            node_type: The node type identifier
            error: Error message
        """
        with self._lock:
            # Remove from executing if present
            self._executing_nodes.pop(node_id, None)
            
            logger.error(
                "Node failed",
                node_id=node_id,
                node_type=node_type,
                error=error,
                workflow_id=self.workflow_id
            )
    
    def on_workflow_failed(self, error: str) -> None:
        """
        Mark workflow as failed.
        
        Args:
            error: Error message
        """
        with self._lock:
            self._status = self.STATUS_FAILED
            self._completed_at = datetime.utcnow()
            self._error = error
            logger.error("Workflow failed", error=error, workflow_id=self.workflow_id)
    
    def get_full_state(self) -> Dict[str, Any]:
        """
        Get complete current state for WebSocket sync.
        
        Returns:
            Dict with all execution state information
        """
        with self._lock:
            now = datetime.utcnow()
            
            result = {
                "workflow_id": self.workflow_id,
                "status": self._status,
                "total_nodes": self.total_nodes,
                "active_runners": self._active_runners,
                "executing_nodes": {
                    node_id: info.to_dict()
                    for node_id, info in self._executing_nodes.items()
                },
                "completed_nodes": [
                    info.to_dict() for info in self._completed_nodes
                ],
                "completed_count": len(self._completed_nodes),
            }
            
            if self._started_at:
                result["started_at"] = self._started_at.isoformat() + "Z"
                result["total_duration_seconds"] = (
                    (self._completed_at or now) - self._started_at
                ).total_seconds()
            
            if self._completed_at:
                result["completed_at"] = self._completed_at.isoformat() + "Z"
            
            if self._error:
                result["error"] = self._error
            
            return result
    
    @property
    def is_running(self) -> bool:
        """Check if workflow is currently running."""
        with self._lock:
            return self._status == self.STATUS_RUNNING
    
    @property
    def status(self) -> str:
        """Get current workflow status."""
        with self._lock:
            return self._status


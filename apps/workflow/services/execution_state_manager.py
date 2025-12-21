"""
Execution State Manager

Manages references to active FlowEngine instances and their state trackers.
Provides state lookup for WebSocket clients on connect.
"""

import sys
import structlog
from typing import Dict, Any, Optional, TYPE_CHECKING
from threading import Lock
from pathlib import Path

# Add core to path for imports
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CORE_PATH = BASE_DIR / 'core'
if str(CORE_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_PATH))

if TYPE_CHECKING:
    from Workflow.flow_engine import FlowEngine

logger = structlog.get_logger(__name__)


class ExecutionStateManager:
    """
    Manages active workflow engine registrations.
    
    Provides:
    - Engine registration/unregistration
    - State lookup for WebSocket sync
    - Thread-safe operations
    """
    
    def __init__(self):
        self._engines: Dict[str, "FlowEngine"] = {}
        self._lock = Lock()
    
    def register_engine(self, workflow_id: str, engine: "FlowEngine") -> None:
        """
        Register an active FlowEngine.
        
        Args:
            workflow_id: The workflow ID
            engine: The FlowEngine instance
        """
        with self._lock:
            self._engines[workflow_id] = engine
            logger.info("Engine registered", workflow_id=workflow_id)
    
    def unregister_engine(self, workflow_id: str) -> None:
        """
        Unregister a FlowEngine.
        
        Args:
            workflow_id: The workflow ID
        """
        with self._lock:
            if workflow_id in self._engines:
                del self._engines[workflow_id]
                logger.info("Engine unregistered", workflow_id=workflow_id)
    
    def get_engine(self, workflow_id: str) -> Optional["FlowEngine"]:
        """
        Get a registered FlowEngine.
        
        Args:
            workflow_id: The workflow ID
            
        Returns:
            The FlowEngine instance or None if not found
        """
        with self._lock:
            return self._engines.get(workflow_id)
    
    def get_state(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current execution state for a workflow.
        
        Args:
            workflow_id: The workflow ID
            
        Returns:
            State dict or None if workflow is not running
        """
        with self._lock:
            engine = self._engines.get(workflow_id)
            if engine and engine.state_tracker:
                return engine.state_tracker.get_full_state()
            
            # Return idle state if no engine is running
            return {
                "workflow_id": workflow_id,
                "status": "idle",
                "executing_nodes": {},
                "completed_nodes": [],
                "completed_count": 0,
            }
    
    def is_running(self, workflow_id: str) -> bool:
        """
        Check if a workflow is currently running.
        
        Args:
            workflow_id: The workflow ID
            
        Returns:
            True if running, False otherwise
        """
        with self._lock:
            engine = self._engines.get(workflow_id)
            if engine and engine.state_tracker:
                return engine.state_tracker.is_running
            return False
    
    def get_all_running_workflows(self) -> Dict[str, Dict[str, Any]]:
        """
        Get states for all running workflows.
        
        Returns:
            Dict mapping workflow_id to state
        """
        with self._lock:
            result = {}
            for workflow_id, engine in self._engines.items():
                if engine.state_tracker:
                    result[workflow_id] = engine.state_tracker.get_full_state()
            return result


# Global singleton instance
execution_state_manager = ExecutionStateManager()


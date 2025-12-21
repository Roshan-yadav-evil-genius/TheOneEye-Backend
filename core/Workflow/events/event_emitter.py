"""
Workflow Event Emitter

A simple, framework-agnostic event emitter for workflow execution events.
Allows subscribers to listen for events like node_started, node_completed, etc.
"""

from typing import Dict, List, Callable, Any
import structlog

logger = structlog.get_logger(__name__)


class WorkflowEventEmitter:
    """
    Event emitter for workflow execution events.
    
    Events:
        - node_started: Emitted when a node begins execution
        - node_completed: Emitted when a node finishes execution
        - node_failed: Emitted when a node execution fails
        - workflow_completed: Emitted when the entire workflow completes
        - workflow_failed: Emitted when the workflow fails
    """
    
    # Event type constants
    NODE_STARTED = "node_started"
    NODE_COMPLETED = "node_completed"
    NODE_FAILED = "node_failed"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    
    def __init__(self, workflow_id: str = None):
        """
        Initialize the event emitter.
        
        Args:
            workflow_id: Optional workflow ID for logging context
        """
        self.workflow_id = workflow_id
        self._subscribers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
    
    def subscribe(self, event_type: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Subscribe to an event type.
        
        Args:
            event_type: The event type to subscribe to
            callback: Function to call when event is emitted. Receives event data dict.
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        logger.debug("Event subscriber added", event_type=event_type, workflow_id=self.workflow_id)
    
    def subscribe_all(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """
        Subscribe to all event types.
        
        Args:
            callback: Function to call for any event. Receives (event_type, data).
        """
        for event_type in [
            self.NODE_STARTED, 
            self.NODE_COMPLETED, 
            self.NODE_FAILED, 
            self.WORKFLOW_COMPLETED, 
            self.WORKFLOW_FAILED
        ]:
            self.subscribe(event_type, lambda data, et=event_type: callback(et, data))
    
    def unsubscribe(self, event_type: str, callback: Callable[[Dict[str, Any]], None]) -> bool:
        """
        Unsubscribe from an event type.
        
        Args:
            event_type: The event type to unsubscribe from
            callback: The callback to remove
            
        Returns:
            True if callback was found and removed, False otherwise
        """
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
                return True
            except ValueError:
                return False
        return False
    
    def emit(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Emit an event to all subscribers.
        
        Args:
            event_type: The type of event to emit
            data: Event data to pass to subscribers
        """
        # Add workflow_id to data if available
        if self.workflow_id:
            data = {"workflow_id": self.workflow_id, **data}
        
        subscribers = self._subscribers.get(event_type, [])
        
        if subscribers:
            logger.debug(
                "Emitting event",
                event_type=event_type,
                subscriber_count=len(subscribers),
                workflow_id=self.workflow_id
            )
        
        for callback in subscribers:
            try:
                callback(data)
            except Exception as e:
                logger.error(
                    "Error in event subscriber",
                    event_type=event_type,
                    error=str(e),
                    workflow_id=self.workflow_id
                )
    
    def clear_subscribers(self, event_type: str = None) -> None:
        """
        Clear all subscribers for an event type, or all subscribers if no type specified.
        
        Args:
            event_type: Optional event type to clear. If None, clears all.
        """
        if event_type:
            self._subscribers[event_type] = []
        else:
            self._subscribers.clear()
    
    # Convenience methods for common events
    
    def emit_node_started(self, node_id: str, node_type: str) -> None:
        """Emit a node_started event."""
        self.emit(self.NODE_STARTED, {
            "node_id": node_id,
            "node_type": node_type,
        })
    
    def emit_node_completed(
        self, 
        node_id: str, 
        node_type: str,
        output_data: Dict[str, Any] = None,
        route: str = None
    ) -> None:
        """
        Emit a node_completed event.
        
        Args:
            node_id: The node ID
            node_type: The node type identifier
            output_data: Optional output data from the node
            route: Optional route taken (for conditional nodes: "yes" or "no")
        """
        data = {
            "node_id": node_id,
            "node_type": node_type,
        }
        if output_data is not None:
            data["output_data"] = output_data
        if route is not None:
            data["route"] = route
        
        self.emit(self.NODE_COMPLETED, data)
    
    def emit_node_failed(self, node_id: str, node_type: str, error: str) -> None:
        """Emit a node_failed event."""
        self.emit(self.NODE_FAILED, {
            "node_id": node_id,
            "node_type": node_type,
            "error": error,
        })
    
    def emit_workflow_completed(self, status: str = "success") -> None:
        """Emit a workflow_completed event."""
        self.emit(self.WORKFLOW_COMPLETED, {
            "status": status,
        })
    
    def emit_workflow_failed(self, error: str) -> None:
        """Emit a workflow_failed event."""
        self.emit(self.WORKFLOW_FAILED, {
            "error": error,
        })


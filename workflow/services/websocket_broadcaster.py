"""
WebSocket Broadcaster Service

Broadcasts workflow execution events to connected WebSocket clients.
Uses Django Channels' channel layer for group messaging.
"""

import structlog
from typing import Dict, Any
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = structlog.get_logger(__name__)


class WebSocketBroadcaster:
    """
    Broadcasts events to WebSocket clients subscribed to a workflow.
    
    Uses Django Channels' channel layer to send messages to groups.
    Each workflow has its own group: workflow_{workflow_id}
    """
    
    def __init__(self):
        self._channel_layer = None
    
    @property
    def channel_layer(self):
        """Lazy-load channel layer to avoid import issues."""
        if self._channel_layer is None:
            self._channel_layer = get_channel_layer()
        return self._channel_layer
    
    def broadcast_event(
        self, 
        workflow_id: str, 
        event_type: str, 
        data: Dict[str, Any]
    ) -> None:
        """
        Broadcast an event to all clients subscribed to a workflow.
        
        Args:
            workflow_id: The workflow ID
            event_type: Type of event (e.g., 'node_started', 'node_completed')
            data: Event data to send
        """
        if not self.channel_layer:
            logger.warning("Channel layer not available, cannot broadcast")
            return
        
        group_name = f"workflow_{workflow_id}"
        
        try:
            async_to_sync(self.channel_layer.group_send)(
                group_name,
                {
                    "type": "workflow.event",  # Maps to workflow_event method in consumer
                    "event_type": event_type,
                    "data": data,
                }
            )
            
            logger.debug(
                "Event broadcasted",
                workflow_id=workflow_id,
                event_type=event_type,
            )
        except Exception as e:
            logger.error(
                "Failed to broadcast event",
                workflow_id=workflow_id,
                event_type=event_type,
                error=str(e)
            )
    
    def broadcast_node_started(
        self, 
        workflow_id: str, 
        node_id: str, 
        node_type: str,
        started_at: str
    ) -> None:
        """Broadcast a node_started event."""
        self.broadcast_event(workflow_id, "node_started", {
            "node_id": node_id,
            "node_type": node_type,
            "started_at": started_at,
        })
    
    def broadcast_node_completed(
        self, 
        workflow_id: str, 
        node_id: str,
        node_type: str,
        duration: float,
        route: str = None,
        output_data: Dict[str, Any] = None
    ) -> None:
        """Broadcast a node_completed event."""
        data = {
            "node_id": node_id,
            "node_type": node_type,
            "duration": duration,
        }
        if route:
            data["route"] = route
        if output_data:
            data["output_data"] = output_data
        
        self.broadcast_event(workflow_id, "node_completed", data)
    
    def broadcast_node_failed(
        self, 
        workflow_id: str, 
        node_id: str, 
        node_type: str,
        error: str
    ) -> None:
        """Broadcast a node_failed event."""
        self.broadcast_event(workflow_id, "node_failed", {
            "node_id": node_id,
            "node_type": node_type,
            "error": error,
        })
    
    def broadcast_workflow_completed(
        self, 
        workflow_id: str, 
        status: str,
        duration: float
    ) -> None:
        """Broadcast a workflow_completed event."""
        self.broadcast_event(workflow_id, "workflow_completed", {
            "status": status,
            "duration": duration,
        })
    
    def broadcast_workflow_failed(
        self, 
        workflow_id: str, 
        error: str
    ) -> None:
        """Broadcast a workflow_failed event."""
        self.broadcast_event(workflow_id, "workflow_failed", {
            "error": error,
        })


# Global singleton instance
websocket_broadcaster = WebSocketBroadcaster()


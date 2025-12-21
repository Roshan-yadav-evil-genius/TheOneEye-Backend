"""
WebSocket consumer for workflow execution real-time updates.

Handles WebSocket connections for clients monitoring workflow execution.
Provides full state sync on connect and real-time event updates.
"""

import json
import structlog
from channels.generic.websocket import AsyncWebsocketConsumer
from .services.redis_state_store import redis_state_store

logger = structlog.get_logger(__name__)


class WorkflowExecutionConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for workflow execution monitoring.
    
    Features:
    - Joins workflow-specific channel group
    - Sends full state sync on connect
    - Receives and forwards execution events
    """
    
    async def connect(self):
        """Handle WebSocket connection."""
        self.workflow_id = self.scope['url_route']['kwargs']['workflow_id']
        self.group_name = f"workflow_{self.workflow_id}"
        
        # Join the workflow channel group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        
        logger.info(
            "WebSocket connected",
            workflow_id=self.workflow_id,
            channel=self.channel_name
        )
        
        # Send full state sync to the newly connected client
        await self._send_state_sync()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Leave the workflow channel group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        
        logger.info(
            "WebSocket disconnected",
            workflow_id=self.workflow_id,
            channel=self.channel_name,
            close_code=close_code
        )
    
    async def receive(self, text_data):
        """
        Handle incoming WebSocket messages.
        
        Currently supports:
        - ping: Returns pong for connection health check
        - request_state: Requests full state sync
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
            
            elif message_type == 'request_state':
                await self._send_state_sync()
            
        except json.JSONDecodeError as e:
            logger.warning("Invalid JSON received", error=str(e))
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
    
    async def _send_state_sync(self):
        """Send full execution state to this client (reads from Redis)."""
        state = redis_state_store.get_state(self.workflow_id)
        
        # If no state in Redis, return idle state
        if state is None:
            state = {
                "workflow_id": self.workflow_id,
                "status": "idle",
                "executing_nodes": {},
                "completed_nodes": [],
                "completed_count": 0,
            }
        
        await self.send(text_data=json.dumps({
            'type': 'state_sync',
            'state': state
        }))
        
        logger.debug(
            "State sync sent",
            workflow_id=self.workflow_id,
            status=state.get('status') if state else None
        )
    
    # Channel layer event handlers (called via group_send)
    
    async def workflow_event(self, event):
        """
        Handle workflow events from channel layer.
        
        Events are sent via group_send with type 'workflow.event'.
        This method forwards them to the WebSocket client.
        """
        await self.send(text_data=json.dumps({
            'type': event['event_type'],
            **event['data']
        }))


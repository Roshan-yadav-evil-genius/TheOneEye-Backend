"""
Webhook Producer Node

Single Responsibility: Listen for incoming webhook data and trigger workflow.

This node handles:
- Subscribing to a webhook channel based on webhook_id
- Blocking indefinitely until data arrives (production mode)
- Accepting direct input data (API mode)
- Returning received data to downstream nodes

This node supports both production and API workflow types:
- Production mode: Subscribes to Redis pub/sub and blocks until data arrives
- API mode: Accepts input data directly from the execute endpoint (no Redis wait)
"""

import structlog
from datetime import datetime
from typing import Optional, List

from ....Core.Node.Core import ProducerNode, NodeOutput, PoolType, ExecutionCompleted
from ....Core.Form import BaseForm
from Workflow.storage.webhook_pubsub_store import webhook_pubsub_store
from .form import WebhookProducerForm

logger = structlog.get_logger(__name__)


class WebhookProducerNode(ProducerNode):
    """
    Producer node that listens for incoming webhook data.
    
    Behavior:
    - Subscribes to Redis pub/sub channel for the configured webhook_id
    - Blocks indefinitely until data is received
    - Works in production mode, standalone mode, and development mode
    - Returns ExecutionCompleted when workflow is stopped
    
    Output:
    - data.webhook.webhook_id: The webhook ID that received data
    - data.webhook.data: The received webhook payload
    - data.webhook.timestamp: When the data was received
    """
    
    def __init__(self, config):
        super().__init__(config)
        self._subscriber_connection = None
    
    @classmethod
    def identifier(cls) -> str:
        """Unique identifier for this node type."""
        return "webhook-producer"
    
    @property
    def execution_pool(self) -> PoolType:
        """Use ASYNC pool - I/O operation (Redis pub/sub)."""
        return PoolType.ASYNC
    
    @property
    def label(self) -> str:
        """Human-readable label for UI display."""
        return "Webhook Producer"
    
    @property
    def description(self) -> str:
        """Description of what this node does."""
        return "Listens for incoming webhook data. External systems POST to /api/webhooks/{webhook_id} to trigger this node."
    
    @property
    def icon(self) -> str:
        """Icon identifier for UI display."""
        return "webhook"

    @property
    def supported_workflow_types(self) -> List[str]:
        """
        WebhookProducerNode supports both production and API workflows.
        
        In production mode: Blocks indefinitely waiting for webhook data.
        In API mode: Receives webhook data as part of request-response flow.
        """
        return ['production', 'api']
    
    def get_form(self) -> Optional[BaseForm]:
        """Return the form instance for this node."""
        return WebhookProducerForm()
    
    async def setup(self):
        """Initialize resources."""
        logger.debug("Webhook Producer setup", node_id=self.node_config.id)
    
    async def execute(self, node_data: NodeOutput) -> NodeOutput:
        """
        Execute the webhook producer node.
        
        Behavior depends on execution mode:
        - API mode (__api_mode__ in metadata): Uses provided input directly
        - Production mode: Subscribes to Redis pub/sub and blocks until data arrives
        
        Args:
            node_data: Output from the previous node. In API mode, contains the input data.
            
        Returns:
            NodeOutput with webhook data, or ExecutionCompleted when stopped
        """
        # Get webhook_id from form
        webhook_id = self.form.get_field_value('webhook_id')
        
        if not webhook_id:
            raise ValueError("webhook_id is required")
        
        # Check if running in API mode (input already provided)
        is_api_mode = False
        if hasattr(node_data, 'metadata') and isinstance(node_data.metadata, dict):
            is_api_mode = node_data.metadata.get('__api_mode__', False)
        
        if is_api_mode:
            # API mode: Use provided input directly (no Redis subscribe)
            return await self._execute_api_mode(node_data, webhook_id)
        else:
            # Production mode: Subscribe to Redis and wait for data
            return await self._execute_production_mode(node_data, webhook_id)
    
    async def _execute_api_mode(self, node_data: NodeOutput, webhook_id: str) -> NodeOutput:
        """
        API mode execution: Use provided input data directly.
        
        In API mode, the input data is passed directly from the HTTP request
        instead of waiting for Redis pub/sub.
        
        Args:
            node_data: NodeOutput containing the input data from API request
            webhook_id: The webhook identifier
            
        Returns:
            NodeOutput with formatted webhook data
        """
        logger.info(
            "API mode: Processing webhook input directly",
            node_id=self.node_config.id,
            webhook_id=webhook_id
        )
        
        # Extract request context from metadata (passed from execute endpoint)
        request_context = {}
        if hasattr(node_data, 'metadata') and isinstance(node_data.metadata, dict):
            request_context = node_data.metadata.get('__request_context__', {})
        
        # In API mode, the input data is already in node_data.data
        # We format it the same way as production mode for consistency
        output_key = self.get_unique_output_key(node_data, 'webhook')
        
        # Store the input data in the webhook format, using actual request context
        node_data.data[output_key] = {
            'webhook_id': webhook_id,
            'data': {
                'body': node_data.data.copy(),  # The API input becomes the body
                'headers': request_context.get('headers', {}),
                'method': request_context.get('method', 'POST'),
                'query_params': request_context.get('query_params', {})
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(
            "API mode: Webhook input processed",
            node_id=self.node_config.id,
            webhook_id=webhook_id,
            execution_count=self.execution_count + 1,
            has_headers=bool(request_context.get('headers')),
            has_query_params=bool(request_context.get('query_params'))
        )
        
        return NodeOutput(
            id=node_data.id,
            data=node_data.data,
            metadata={
                "sourceNodeID": self.node_config.id,
                "sourceNodeName": self.node_config.type,
                "operation": "webhook_receive",
                "webhook_id": webhook_id,
                "iteration": self.execution_count + 1,
                "__api_mode__": True  # Preserve API mode flag for downstream nodes
            }
        )
    
    async def _execute_production_mode(self, node_data: NodeOutput, webhook_id: str) -> NodeOutput:
        """
        Production mode execution: Subscribe to Redis and wait for data.
        
        Blocks indefinitely until webhook data is received via Redis pub/sub.
        
        Args:
            node_data: Output from the previous node (ignored for ProducerNode)
            webhook_id: The webhook identifier to subscribe to
            
        Returns:
            NodeOutput with webhook data
        """
        logger.info(
            "Production mode: Waiting for webhook data",
            node_id=self.node_config.id,
            webhook_id=webhook_id
        )
        
        try:
            # Subscribe and wait for data (blocks indefinitely)
            received_data = await webhook_pubsub_store.subscribe(
                webhook_id,
                connection=self._subscriber_connection
            )
            
            # Store received data in output
            output_key = self.get_unique_output_key(node_data, 'webhook')
            node_data.data[output_key] = {
                'webhook_id': webhook_id,
                'data': received_data,
                'timestamp': node_data.metadata.get('timestamp') if hasattr(node_data, 'metadata') else None
            }
            
            logger.info(
                "Production mode: Received webhook data",
                node_id=self.node_config.id,
                webhook_id=webhook_id,
                execution_count=self.execution_count + 1
            )
            
            return NodeOutput(
                id=node_data.id,
                data=node_data.data,
                metadata={
                    "sourceNodeID": self.node_config.id,
                    "sourceNodeName": self.node_config.type,
                    "operation": "webhook_receive",
                    "webhook_id": webhook_id,
                    "iteration": self.execution_count + 1
                }
            )
            
        except Exception as e:
            logger.error(
                "Production mode: Error receiving webhook data",
                node_id=self.node_config.id,
                webhook_id=webhook_id,
                error=str(e),
                exc_info=True
            )
            raise
    
    async def cleanup(self, node_data: Optional[NodeOutput] = None):
        """Clean up subscription connection."""
        if self._subscriber_connection is not None:
            try:
                self._subscriber_connection.close()
                self._subscriber_connection = None
                logger.debug(
                    "Webhook subscription connection closed",
                    node_id=self.node_config.id
                )
            except Exception as e:
                logger.warning(
                    "Error closing webhook subscription connection",
                    node_id=self.node_config.id,
                    error=str(e)
                )

"""
Webhook Producer Node

Single Responsibility: Listen for incoming webhook data and trigger workflow.

This node handles:
- Subscribing to a webhook channel based on webhook_id
- Blocking indefinitely until data arrives (all execution modes)
- Returning received data to downstream nodes

This node supports both production and API workflow types as it can adapt its
behavior based on the workflow execution mode.
"""

import structlog
from typing import Optional, List

from ....Core.Node.Core import ProducerNode, NodeOutput, PoolType, ExecutionCompleted
from ....Core.Form.Core.BaseForm import BaseForm
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
        Subscribe to webhook channel and wait for data.
        
        Blocks indefinitely until webhook data is received.
        Works in all execution modes: production, standalone, and development.
        
        Args:
            node_data: Output from the previous node (ignored for ProducerNode)
            
        Returns:
            NodeOutput with webhook data, or ExecutionCompleted when stopped
        """
        # Get webhook_id from form
        webhook_id = self.form.get_field_value('webhook_id')
        
        if not webhook_id:
            raise ValueError("webhook_id is required")
        
        logger.info(
            "Waiting for webhook data",
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
                "Received webhook data",
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
                "Error receiving webhook data",
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

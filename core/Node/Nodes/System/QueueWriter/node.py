"""
QueueWriter Node

Single Responsibility: Push workflow data to queues.

This node is production-only because it writes to queues that are consumed
by production workflows, which is incompatible with request-response (API) workflows.
"""

import structlog
from typing import List

from ....Core.Node.Core import NonBlockingNode, NodeOutput, PoolType
from .....Workflow.storage.data_store import DataStore

logger = structlog.get_logger(__name__)


class QueueWriter(NonBlockingNode):
    @classmethod
    def identifier(cls) -> str:
        return "queue-node-writer"

    @property
    def execution_pool(self) -> PoolType:
        return PoolType.ASYNC

    @property
    def supported_workflow_types(self) -> List[str]:
        """
        QueueWriter only supports production workflows.
        
        This node writes to queues that are consumed by production workflows,
        which is incompatible with request-response (API) workflows.
        """
        return ['production']

    async def setup(self):
        """Initialize the DataStore connection once during node setup."""
        self.data_store = DataStore()

    async def cleanup(self, node_data: NodeOutput = None):
        """
        Push Sentinel Pill to the queue during cleanup to propagate termination.
        """
        await self.execute(node_data)
        await self.data_store.close()

    async def execute(self, node_data: NodeOutput) -> NodeOutput:
        """
        Execute the queue node by pushing data to the queue.
        
        Uses DataStore's queue service for queue operations.
        """
        # Extract queue name from node config (validated by NodeValidator)
        queue_name = self.node_config.data.config["queue_name"]
        
        # Push data to queue using the new SRP-compliant API
        await self.data_store.queue.push(queue_name, node_data.to_dict())
        
        return node_data


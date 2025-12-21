"""
QueueReader Node

Single Responsibility: Pop workflow data from queues.
"""

import structlog

from Workflow.flow_utils import node_type
from ....Core.Node.Core import ProducerNode, NodeOutput, PoolType
from ....Core.Node.Core.Data import ExecutionCompleted
from Workflow.storage.data_store import DataStore

logger = structlog.get_logger(__name__)


class QueueReader(ProducerNode):
    @classmethod
    def identifier(cls) -> str:
        return "queue-reader-dummy"

    @property
    def execution_pool(self) -> PoolType:
        return PoolType.ASYNC

    async def setup(self):
        """Initialize the DataStore connection once during node setup."""
        self.data_store = DataStore()

    async def execute(self, node_data: NodeOutput) -> NodeOutput:
        """
        Execute the queue reader by popping data from the queue.
        
        Uses DataStore's queue service for queue operations.
        Blocks indefinitely until data is available.
        """
        # Extract queue name from node config (validated by NodeValidator)
        queue_name = self.node_config.data.config["queue_name"]
        
        # Pop data from queue using the new SRP-compliant API
        # (blocks indefinitely until data arrives)
        result = await self.data_store.queue.pop(queue_name, timeout=0)

        # Check for Sentinel Pill in popped data
        if result.get("metadata", {}).get("__execution_completed__"):
            logger.info("Received Sentinel Pill from queue", queue=queue_name)
            return ExecutionCompleted(**result)

        logger.info(
            "Popped from queue",
            queue_name=queue_name,
            node_id=self.node_config.id,
            node_type=f"{node_type(self)}({self.identifier()})"
        )
        
        return NodeOutput(**result)


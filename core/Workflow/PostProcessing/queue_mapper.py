from typing import Optional
import structlog
from Node.Core.Node.Core.BaseNode import BaseNode
from Node.Core.Node.Core.Data import NodeConfigData
from Node.Nodes.System.QueueWriter import QueueWriter
from Node.Nodes.System.QueueReader import QueueReader
from ..flow_node import FlowNode
from . import PostProcessor

logger = structlog.get_logger(__name__)


class QueueMapper(PostProcessor):
    """
    Handles automatic queue name assignment for connected QueueWriter-QueueReader pairs.
    Follows Single Responsibility Principle - only handles queue mapping logic.
    """

    def execute(self) -> None:
        """
        Process the graph and assign unique queue names to connected QueueWriter-QueueReader pairs.
        """
        logger.info("Mapping queues for connected QueueWriter-QueueReader pairs...")
        
        mapped_count = 0
        for node_id, workflow_node in self.graph.node_map.items():
            # Check if this node is a QueueWriter
            if not self._is_queue_node(workflow_node.instance):
                continue
            
            # MULTIPLE BRANCH SUPPORT: Must iterate through lists because QueueWriter
            # can connect to multiple QueueReaders through different branches
            # OUTER LOOP: Iterate through all branch keys (e.g., "default", "yes", "no")
            for next_key, next_nodes_list in workflow_node.next.items():
                # INNER LOOP: Iterate through all nodes in each branch list
                # REASON: A QueueWriter can have multiple QueueReader connections, each
                # in a different branch. We need to map queue names for all of them.
                for next_node in next_nodes_list:
                    # Check if the connected node is a QueueReader
                    if self._is_queue_reader(next_node.instance):
                        # Generate unique queue name for this QueueWriter-QueueReader pair
                        # Each pair gets its own queue name, even if from same QueueWriter
                        queue_name = self._generate_queue_name(node_id, next_node.id)
                        
                        # Assign queue name to both nodes' configs
                        self._assign_queue_name(workflow_node, next_node, queue_name)
                        mapped_count += 1
                        logger.info(
                            f"Auto-assigned queue name '{queue_name}' to QueueWriter '{node_id}' and QueueReader '{next_node.id}'"
                        )
        
        logger.info(f"Queue mapping completed. Mapped {mapped_count} QueueWriter-QueueReader pairs.")

    def _is_queue_node(self, node_instance: BaseNode) -> bool:
        """
        Check if node is QueueWriter or a subclass.

        Args:
            node_instance: BaseNode instance to check

        Returns:
            True if node is QueueWriter or subclass, False otherwise
        """
        return isinstance(node_instance, QueueWriter)

    def _is_queue_reader(self, node_instance: BaseNode) -> bool:
        """
        Check if node is QueueReader or a subclass.

        Args:
            node_instance: BaseNode instance to check

        Returns:
            True if node is QueueReader or subclass, False otherwise
        """
        return isinstance(node_instance, QueueReader)

    def _generate_queue_name(self, source_id: str, target_id: str) -> str:
        """
        Generate unique queue name from source and target node IDs.

        Args:
            source_id: ID of the source QueueWriter
            target_id: ID of the target QueueReader

        Returns:
            Unique queue name string
        """
        return f"queue_{source_id}_{target_id}"

    def _assign_queue_name(
        self, source_node: FlowNode, target_node: FlowNode, queue_name: str
    ) -> None:
        """
        Assign queue name to both source and target nodes' configs.

        Args:
            source_node: FlowNode instance (QueueWriter)
            target_node: FlowNode instance (QueueReader)
            queue_name: Queue name to assign
        """
        # Ensure config.data exists for source node
        if source_node.instance.node_config.data is None:
            source_node.instance.node_config.data = NodeConfigData()
        if source_node.instance.node_config.data.config is None:
            source_node.instance.node_config.data.config = {}

        # Ensure config.data exists for target node
        if target_node.instance.node_config.data is None:
            target_node.instance.node_config.data = NodeConfigData()
        if target_node.instance.node_config.data.config is None:
            target_node.instance.node_config.data.config = {}

        # Only assign if not already set or is "default"
        if source_node.instance.node_config.data.config.get("queue_name") in (None, "default"):
            source_node.instance.node_config.data.config["queue_name"] = queue_name

        if target_node.instance.node_config.data.config.get("queue_name") in (None, "default"):
            target_node.instance.node_config.data.config["queue_name"] = queue_name

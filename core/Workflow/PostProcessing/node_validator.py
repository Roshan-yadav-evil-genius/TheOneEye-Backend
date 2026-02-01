import structlog
from . import PostProcessor

logger = structlog.get_logger(__name__)


class NodeValidator(PostProcessor):
    """
    Handles validation of all nodes in the workflow graph.
    Follows Single Responsibility Principle - only handles node validation.
    """

    def execute(self, **kwargs) -> None:
        """
        Validate nodes in the graph by calling their ready() method.
        If validate_only_node_ids is provided (set of node IDs), only those nodes are validated.
        Raises ValueError if any validated node is not ready.
        """
        validate_only_node_ids = kwargs.get("validate_only_node_ids")
        if validate_only_node_ids is not None:
            node_ids_to_validate = [
                nid for nid in validate_only_node_ids
                if nid in self.graph.node_map
            ]
            logger.info(
                "Validating scope-only nodes in workflow...",
                scope_count=len(node_ids_to_validate),
                scope_node_ids=list(node_ids_to_validate)[:20],
            )
        else:
            node_ids_to_validate = list(self.graph.node_map.keys())
            logger.info("Validating all nodes in workflow...")

        failed_nodes = []
        for node_id in node_ids_to_validate:
            workflow_node = self.graph.node_map.get(node_id)
            if workflow_node is None:
                continue
            node = workflow_node.instance
            if not node.is_ready():
                # Get errors from form if available
                if node.form is not None:
                    # Use node's built-in method for clean error extraction (no HTML)
                    error_list = node._extract_clean_error_messages(node.form)
                    failed_nodes.append(f"Node '{node_id}': {error_list}")
                else:
                    failed_nodes.append(f"Node '{node_id}': validation failed")
            else:
                # Mark node as validated so init() won't re-validate in async context
                node.mark_validated()

        if failed_nodes:
            error_text = "Workflow validation failed:\n" + "\n".join(failed_nodes)
            logger.error(error_text)
            raise ValueError(error_text)
        
        logger.info("All nodes validated successfully.")

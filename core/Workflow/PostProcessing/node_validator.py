import structlog
from . import PostProcessor

logger = structlog.get_logger(__name__)


class NodeValidator(PostProcessor):
    """
    Handles validation of all nodes in the workflow graph.
    Follows Single Responsibility Principle - only handles node validation.
    """

    def execute(self) -> None:
        """
        Validate all nodes in the graph by calling their ready() method.
        Raises ValueError if any node is not ready.
        """
        logger.info("Validating all nodes in workflow...")
        
        failed_nodes = []
        for node_id, workflow_node in self.graph.node_map.items():
            node = workflow_node.instance
            if not node.is_ready():
                # Get errors from form if available
                if node.form is not None:
                    errors = node.form.errors
                    error_list = ', '.join(f"{k}: {v}" for k, v in errors.items())
                    failed_nodes.append(f"Node '{node_id}': {error_list}")
                else:
                    failed_nodes.append(f"Node '{node_id}': validation failed")
        
        if failed_nodes:
            error_text = "Workflow validation failed:\n" + "\n".join(failed_nodes)
            logger.error(error_text)
            raise ValueError(error_text)
        
        logger.info("All nodes validated successfully.")

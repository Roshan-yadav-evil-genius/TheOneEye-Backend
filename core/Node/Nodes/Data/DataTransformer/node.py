"""
DataTransformer Node

Single Responsibility: Transform incoming data using a JSON template with Jinja expressions.
The rendered JSON is forwarded to downstream nodes.
"""

import json
from typing import Optional
import structlog

from ....Core.Node.Core import BlockingNode, NodeOutput, PoolType
from ....Core.Form import BaseForm
from .form import DataTransformerForm

logger = structlog.get_logger(__name__)


class DataTransformer(BlockingNode):
    """
    Transform data using a JSON template with Jinja support.
    
    Users define the exact output structure in a JSON template,
    using Jinja expressions to reference incoming data fields.
    This allows dropping, adding, renaming, and transforming fields
    in a single, intuitive configuration.
    
    Example template:
    {
      "name": "{{ data.webhook.data.body.name }}",
      "email": "{{ data.webhook.data.body.email }}",
      "count_doubled": {{ data.webhook.data.body.count * 2 }}
    }
    """
    
    @classmethod
    def identifier(cls) -> str:
        """Unique identifier for this node type."""
        return "data-transformer"

    @property
    def label(self) -> str:
        """Display name for UI."""
        return "Data Transformer"
    
    @property
    def description(self) -> str:
        """Node description for documentation."""
        return "Transform data using a JSON template with Jinja expressions"
    
    @property
    def icon(self) -> str:
        """Icon identifier for UI."""
        return "transform"

    def get_form(self) -> Optional[BaseForm]:
        """Return the configuration form."""
        return DataTransformerForm()

    @property
    def execution_pool(self) -> PoolType:
        """Use THREAD pool - lightweight JSON parsing."""
        return PoolType.THREAD

    def execute(self, node_data: NodeOutput) -> NodeOutput:
        """
        Render the JSON template and forward the result.
        
        The Jinja templates are already rendered by populate_form_values()
        before this method is called, so form.get_field_value() returns
        the fully rendered JSON string.
        
        Args:
            node_data: The NodeOutput from the previous node.
            
        Returns:
            NodeOutput with the transformed data (replaces all previous data).
            
        Raises:
            ValueError: If the rendered template is not valid JSON.
        """
        # Get rendered template (Jinja already processed by populate_form_values)
        rendered_json = self.form.get_field_value("output_template")
        
        if not rendered_json or not rendered_json.strip():
            raise ValueError("Output template is required")
        
        try:
            # Parse the rendered JSON
            transformed_data = json.loads(rendered_json)
        except json.JSONDecodeError as e:
            logger.error(
                "Invalid JSON after rendering",
                error=str(e),
                rendered=rendered_json[:500],  # Log first 500 chars for debugging
                node_id=self.node_config.id
            )
            raise ValueError(f"Invalid JSON in output template: {e}")
        
        logger.info(
            "Data transformation completed",
            node_id=self.node_config.id,
            keys=list(transformed_data.keys()) if isinstance(transformed_data, dict) else type(transformed_data).__name__
        )
        
        # Return transformed data as the complete new output (overwrites previous data)
        return NodeOutput(
            id=node_data.id,
            data=transformed_data,
            metadata={
                "sourceNodeID": self.node_config.id,
                "sourceNodeName": self.node_config.type,
                "operation": "data_transform"
            }
        )

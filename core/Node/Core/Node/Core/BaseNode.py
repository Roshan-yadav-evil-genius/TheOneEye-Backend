from abc import ABC
from typing import Optional
import re

import structlog
from Node.Core.Form.Core.FormSerializer import FormSerializer
from .Data import NodeConfig, NodeOutput, ExecutionCompleted
from .BaseNodeProperty import BaseNodeProperty
from .BaseNodeMethod import BaseNodeMethod

logger = structlog.get_logger(__name__)

# Jinja template detection pattern
JINJA_PATTERN = re.compile(r'\{\{.*?\}\}')


def contains_jinja_template(value) -> bool:
    """Check if a value contains Jinja template syntax."""
    if value is None:
        return False
    return bool(JINJA_PATTERN.search(str(value)))

class BaseNode(BaseNodeProperty, BaseNodeMethod, ABC):
    """
    Dont Use This Class Directly. Use One of the Subclasses Instead.
    This class is used to define the base node class and is not meant to be instantiated directly.
    use for type hinting and inheritance.
    """
    
    def __init__(self, node_config: NodeConfig):
        self.node_config = node_config
        self.form = self.get_form()
        self._populate_form()
        self.execution_count = 0
    
    def _populate_form(self):
        """
        Populate the form with the data from the config.
        """
        if self.form is not None:
            for key, value in self.node_config.data.form.items():
                self.form.update_field(key, value)
            logger.info(f"Form Populated", form=self.form.get_all_field_values(), node_id=self.node_config.id, identifier=f"{self.__class__.__name__}({self.identifier()})")

    def is_ready(self) -> bool:
        """
        Validate that the node has all required config fields.
        For fields with Jinja templates, only checks if required fields have a value.
        Full validation happens at runtime after template rendering.
        
        Returns:
            bool: True if node is ready, False otherwise.
        """
        if self.form is None:
            return True
        return self._validate_template_fields()
    
    def _validate_template_fields(self) -> bool:
        """
        Validate form fields, handling Jinja templates specially.
        For template fields: only check if required fields are not empty.
        For non-template fields: perform full Django validation.
        
        Returns:
            bool: True if validation passes, False otherwise.
        """
        if self.form is None:
            return True
        
        # Clear any existing errors
        self.form._errors = None
        
        form_data = self.node_config.data.form or {}
        
        for field_name, field in self.form.fields.items():
            value = form_data.get(field_name)
            
            if contains_jinja_template(value):
                # For template fields: only check required + not empty
                if field.required and (value is None or str(value).strip() == ''):
                    # Initialize errors if needed
                    if self.form._errors is None:
                        from django.forms.utils import ErrorDict
                        self.form._errors = ErrorDict()
                    self.form._errors[field_name] = self.form.error_class(['This field is required.'])
            else:
                # For non-template fields: perform normal field validation
                try:
                    field.clean(value)
                except Exception as e:
                    if self.form._errors is None:
                        from django.forms.utils import ErrorDict
                        self.form._errors = ErrorDict()
                    self.form._errors[field_name] = self.form.error_class([str(e)])
        
        return not bool(self.form._errors)
    
    async def init(self):
        """
        Initialize the node.
        This method is called before calling execute method.
        It is used to validate the node and set up any necessary resources.
        Default implementation does nothing.
        """

        if not self.is_ready():
            raise ValueError(f"Node {self.node_config.id} is not ready")
        await self.setup()
    
    def populate_form_values(self, node_data: NodeOutput) -> None:
        """
        Render Jinja templates in form fields with runtime data.
        Called before execute() to populate form with actual values.
        
        Args:
            node_data: The NodeOutput containing runtime data for template rendering.
        
        Raises:
            ValueError: If form validation fails after rendering.
        """
        from jinja2 import Template
        
        if self.form is None:
            return
        
        form_data = self.node_config.data.form or {}
        
        for field_name in self.form.fields:
            raw_value = form_data.get(field_name)
            if raw_value is not None and contains_jinja_template(str(raw_value)):
                # Render the Jinja template with node data
                template = Template(str(raw_value))
                rendered_value = template.render(data=node_data.data)
                self.form.update_field(field_name, rendered_value)
                logger.debug(
                    "Rendered template field",
                    field=field_name,
                    raw=raw_value,
                    rendered=rendered_value,
                    node_id=self.node_config.id
                )
        
        # Validate form after rendering
        if not self.form.is_valid():
            raise ValueError(f"Form validation failed after rendering: {self.form.errors}")
        else:
            self.form.validate()
            logger.info(f"Form validation passed", form=self.form.get_all_field_values(), node_id=self.node_config.id, identifier=f"{self.__class__.__name__}({self.identifier()})")
            
    async def run(self, node_data: NodeOutput) -> NodeOutput:
        """
        Main entry point for node execution.
        Populates form values with runtime data, then executes the node.
        
        Args:
            node_data: The NodeOutput from previous node.
            
        Returns:
            NodeOutput: The result of node execution.
        """

        if isinstance(node_data, ExecutionCompleted):
            await self.cleanup(node_data)
            logger.warning("Cleanup completed", node_id=self.node_config.id, identifier=f"{self.__class__.__name__}({self.identifier()})")
            return node_data

        self.populate_form_values(node_data)
        output = await self.execute(node_data)
        self.execution_count += 1
        return output

    async def cleanup(self, node_data: Optional[NodeOutput] = None):
        """
        Cleanup the node resources.
        Called when the node receives an ExecutionCompleted input.
        
        Args:
            node_data: The sentinel signal data, if available.
        """
        pass

    def get_unique_output_key(self, node_data: NodeOutput, base_key: str) -> str:
        """
        Generate a unique output key for this node's data.
        If base_key already exists in node_data.data, appends _2, _3, etc.
        
        This prevents nodes of the same type from overwriting each other's output
        when multiple instances are used in a workflow.
        
        Args:
            node_data: The NodeOutput containing existing data
            base_key: The base key name (e.g., "google_sheets")
        
        Returns:
            Unique key string (e.g., "google_sheets", "google_sheets_2", etc.)
        """
        if base_key not in node_data.data:
            return base_key
        
        counter = 2
        while f"{base_key}_{counter}" in node_data.data:
            counter += 1
        
        return f"{base_key}_{counter}"


class NonBlockingNode(BaseNode, ABC):
    """
    Semantically marks loop-end in the execution model.
    Performs a computation or transformation but does not force the Producer 
    to wait for downstream operations.
    """
    pass


class ProducerNode(BaseNode, ABC):
    """
    Marks loop start. Called first each iteration.
    Starts and controls the loop. Controls timing and triggers downstream nodes.
    """
    
    @property
    def input_ports(self) -> list:
        """Producer nodes have no input ports - they start the flow."""
        return []


class BlockingNode(BaseNode, ABC):
    """
    Performs work that must be completed prior to continuation.
    The LoopManager awaits the Blocking node and all downstream Blocking children 
    in its async chain to complete before proceeding.
    """
    pass

class ConditionalNode(BlockingNode, ABC):
    """
    Base class for logical/conditional nodes that perform decision-making operations.
    Inherits from BlockingNode, ensuring logical operations complete before continuation.
    """
    def __init__(self, config: NodeConfig):
        super().__init__(config)
        self.output: Optional[str] = None
        self.test_result = False

    @property
    def output_ports(self) -> list:
        """Conditional nodes have 'yes' and 'no' output branches."""
        return [
            {"id": "yes", "label": "Yes"},
            {"id": "no", "label": "No"}
        ]

    def set_output(self, output: bool):
        self.test_result = output
        self.output = "yes" if output else "no"


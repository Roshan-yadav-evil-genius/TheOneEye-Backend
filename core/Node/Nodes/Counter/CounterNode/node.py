"""
Counter Node

Single Responsibility: Execute counter iteration with state tracking.

This node handles:
- Maintaining current value state across iterations
- Incrementing/decrementing by step value
- Signaling ExecutionCompleted when bounds are exceeded
"""

import structlog
from typing import Optional

from ....Core.Node.Core import ProducerNode, NodeOutput, PoolType, ExecutionCompleted
from ....Core.Form.Core.BaseForm import BaseForm
from .form import CounterForm

logger = structlog.get_logger(__name__)


class CounterNode(ProducerNode):
    """
    Stateful counter that iterates between min and max values.
    
    Behavior:
    - increment mode: starts at min, increments by step each iteration
    - decrement mode: starts at max, decrements by step each iteration
    - Returns ExecutionCompleted when boundary is exceeded
    
    Output:
    - data.counter.current: Current counter value
    - data.counter.min: Minimum bound
    - data.counter.max: Maximum bound
    - data.counter.step: Step size
    - data.counter.iteration: Current iteration number
    """
    
    def __init__(self, config):
        super().__init__(config)
        self.current_value: Optional[int] = None
    
    @classmethod
    def identifier(cls) -> str:
        """Unique identifier for this node type."""
        return "counter"
    
    @property
    def execution_pool(self) -> PoolType:
        """Use ASYNC pool - no I/O, pure computation."""
        return PoolType.ASYNC
    
    @property
    def label(self) -> str:
        """Human-readable label for UI display."""
        return "Counter"
    
    @property
    def description(self) -> str:
        """Description of what this node does."""
        return "Iterates between min and max values, incrementing or decrement by step"
    
    @property
    def icon(self) -> str:
        """Icon identifier for UI display."""
        return "counter"
    
    def get_form(self) -> Optional[BaseForm]:
        """Return the form instance for this node."""
        return CounterForm()
    
    def _initialize_counter(self):
        """Initialize counter value based on direction (called on first execute)."""
        if self.current_value is not None:
            return  # Already initialized
            
        direction = self.form.cleaned_data.get('direction', 'increment')
        min_value = self.form.cleaned_data.get('min_value', 0)
        max_value = self.form.cleaned_data.get('max_value', 10)
        
        if direction == 'increment':
            self.current_value = min_value
        else:  # decrement
            self.current_value = max_value
        
        logger.info(
            "Counter initialized",
            node_id=self.node_config.id,
            direction=direction,
            start_value=self.current_value,
            min=min_value,
            max=max_value
        )
    
    async def execute(self, previous_node_output: NodeOutput) -> NodeOutput:
        """
        Execute one counter iteration.
        
        Args:
            previous_node_output: Output from the previous node
            
        Returns:
            NodeOutput with counter data, or ExecutionCompleted when done
        """
        # Extract form values
        min_value = self.form.cleaned_data.get('min_value', 0)
        max_value = self.form.cleaned_data.get('max_value', 10)
        direction = self.form.cleaned_data.get('direction', 'increment')
        step = self.form.cleaned_data.get('step', 1)
        
        # Initialize counter on first execution
        self._initialize_counter()
        
        # Check if we've exceeded bounds
        if direction == 'increment' and self.current_value > max_value:
            logger.info(
                "Counter completed (increment exceeded max)",
                node_id=self.node_config.id,
                current=self.current_value,
                max=max_value
            )
            return ExecutionCompleted(
                id=previous_node_output.id,
                data=previous_node_output.data
            )
        
        if direction == 'decrement' and self.current_value < min_value:
            logger.info(
                "Counter completed (decrement below min)",
                node_id=self.node_config.id,
                current=self.current_value,
                min=min_value
            )
            return ExecutionCompleted(
                id=previous_node_output.id,
                data=previous_node_output.data
            )
        
        # Store current value in output with unique key
        output_key = self.get_unique_output_key(previous_node_output, 'counter')
        previous_node_output.data[output_key] = {
            'current': self.current_value,
            'min': min_value,
            'max': max_value,
            'step': step,
            'direction': direction,
            'iteration': self.execution_count + 1
        }
        
        logger.debug(
            "Counter iteration",
            node_id=self.node_config.id,
            current=self.current_value,
            iteration=self.execution_count + 1
        )
        
        # Update for next iteration
        if direction == 'increment':
            self.current_value += step
        else:
            self.current_value -= step
        
        return NodeOutput(
            id=previous_node_output.id,
            data=previous_node_output.data,
            metadata={
                "sourceNodeID": self.node_config.id,
                "sourceNodeName": self.node_config.type,
                "operation": "counter",
                "current_value": self.current_value - (step if direction == 'increment' else -step),
                "iteration": self.execution_count + 1
            }
        )
    
    async def cleanup(self, node_data: Optional[NodeOutput] = None):
        """Reset counter state on cleanup."""
        self.current_value = None
        logger.debug("Counter reset", node_id=self.node_config.id)


"""
Static Delay Node - Blocks execution for a fixed time interval.

This node introduces a configurable fixed delay in the workflow execution.
It holds the NodeData from the previous node for the specified duration,
then passes it to the next node unchanged.
"""

import asyncio
import structlog
from typing import Optional

from ....Core.Node.Core import BlockingNode, NodeOutput, PoolType
from ....Core.Form.Core.BaseForm import BaseForm
from .form import StaticDelayForm
from .._shared.constants import TIME_UNIT_TO_SECONDS

logger = structlog.get_logger(__name__)


class StaticDelayNode(BlockingNode):
    """
    A Blocking Node that holds execution for a fixed time interval.
    
    Configuration:
    - interval: The numeric value of time to wait
    - unit: seconds, minutes, hours, days, or months
    
    Example:
    - interval=5, unit="minutes" -> waits 5 minutes (300 seconds)
    - interval=2, unit="hours" -> waits 2 hours (7200 seconds)
    
    Use Cases:
    - Rate limiting API calls
    - Introducing pauses between operations
    - Throttling workflow execution
    - Simulating processing time
    """
    
    @classmethod
    def identifier(cls) -> str:
        return "static-delay-node"
    
    @property
    def execution_pool(self) -> PoolType:
        return PoolType.ASYNC
    
    @property
    def label(self) -> str:
        return "Static Delay"
    
    @property
    def description(self) -> str:
        return "Holds execution for a fixed time interval"
    
    def get_form(self) -> Optional[BaseForm]:
        return StaticDelayForm()
    
    def _calculate_delay_seconds(self) -> float:
        """Calculate the delay in seconds based on interval and unit."""
        interval = self.form.cleaned_data.get('interval', 0)
        unit = self.form.cleaned_data.get('unit', 'seconds')
        
        multiplier = TIME_UNIT_TO_SECONDS.get(unit, 1)
        return interval * multiplier
    
    def _format_duration(self, seconds: float) -> str:
        """Format seconds into human-readable duration."""
        if seconds < 60:
            return f"{seconds:.1f} seconds"
        elif seconds < 3600:
            return f"{seconds / 60:.1f} minutes"
        elif seconds < 86400:
            return f"{seconds / 3600:.2f} hours"
        else:
            return f"{seconds / 86400:.2f} days"
    
    async def execute(self, previous_node_output: NodeOutput) -> NodeOutput:
        """
        Execute the static delay.
        
        Holds execution for the configured fixed duration,
        then returns the data unchanged to be passed to the next node.
        
        Args:
            previous_node_output: The NodeOutput from the previous node.
            
        Returns:
            NodeOutput: The same data, passed through after the delay.
        """
        delay_seconds = self._calculate_delay_seconds()
        interval = self.form.cleaned_data.get('interval')
        unit = self.form.cleaned_data.get('unit')
        
        logger.info(
            "Static delay starting",
            node_id=self.node_config.id,
            delay=f"{interval} {unit}",
            delay_seconds=delay_seconds
        )
        
        await asyncio.sleep(delay_seconds)
        
        logger.info(
            "Static delay completed",
            node_id=self.node_config.id,
            waited=self._format_duration(delay_seconds)
        )
        
        return NodeOutput(
            id=previous_node_output.id,
            data=previous_node_output.data,
            metadata={
                "sourceNodeID": self.node_config.id,
                "sourceNodeName": self.node_config.type,
                "delayType": "static",
                "delayApplied": f"{interval} {unit}",
                "delaySeconds": delay_seconds
            }
        )


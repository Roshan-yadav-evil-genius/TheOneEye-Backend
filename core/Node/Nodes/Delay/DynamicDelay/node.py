"""
Dynamic Delay Node - Pre-computes randomized delays that sum to exact target time.

This node generates a list of randomized delays at the start, ensuring
the total sum equals exactly the specified time period. Each execution
pops one delay from the list, guaranteeing all executions complete
within the target time window.
"""

import asyncio
import random
import structlog
from typing import Optional, List

from ....Core.Node.Core import BlockingNode, NodeOutput, PoolType
from ....Core.Form.Core.BaseForm import BaseForm
from .form import DynamicDelayForm
from .._shared.constants import TIME_UNIT_TO_SECONDS
from Workflow.storage.data_store import DataStore

logger = structlog.get_logger(__name__)


class DynamicDelayNode(BlockingNode):
    """
    Pre-computes a list of randomized delays that sum to exactly the target time.
    
    How it works:
    1. At first execution, generates a list of random delays with jitter
    2. Normalizes them so sum = exact target time
    3. Stores the list in Redis cache
    4. Each execution pops and applies one delay from the list
    5. When list is empty, regenerates for next cycle
    
    Configuration:
    - total_time: The total time window (e.g., 24)
    - unit: Time unit (e.g., hours)
    - executions: Number of executions in the window (e.g., 20)
    - jitter_percent: Randomness as ±% of base delay (e.g., 30)
    
    Example:
    - Config: 24 hours, 20 executions, 30% jitter
    - Base delay = 72 min
    - Generates: [65, 78, 52, 89, ...] (20 random values around 72 ±30%)
    - Scales so sum = exactly 1440 minutes
    - Final: [62.1, 74.5, 49.7, 85.0, ...] (sum = 1440 min exactly)
    
    This guarantees all 20 executions complete within exactly 24 hours,
    with randomized intervals to avoid detection patterns.
    """
    
    @classmethod
    def identifier(cls) -> str:
        return "dynamic-delay-node"
    
    @property
    def execution_pool(self) -> PoolType:
        return PoolType.ASYNC
    
    @property
    def label(self) -> str:
        return "Dynamic Delay"
    
    @property
    def description(self) -> str:
        return "Randomized delays that sum to exact target time"
    
    def get_form(self) -> Optional[BaseForm]:
        return DynamicDelayForm()
    
    async def setup(self):
        """Initialize DataStore for storing delay list."""
        self.data_store = DataStore()
        self._cache_key = f"delay_node:{self.node_config.id}:delays"
    
    def _generate_delay_list(self) -> List[float]:
        """
        Generate a list of randomized delays that sum to exactly the target time.
        
        Algorithm:
        1. Calculate base delay = total_time / executions
        2. Generate random values with jitter around base delay
        3. Normalize (scale) all values so their sum equals exactly total_time
        
        Returns:
            List[float]: List of delay values in seconds
        """
        total_time = self.form.cleaned_data.get('total_time', 1)
        unit = self.form.cleaned_data.get('unit', 'hours')
        executions = self.form.cleaned_data.get('executions', 1)
        jitter_percent = self.form.cleaned_data.get('jitter_percent') or 30
        
        # Convert total time to seconds
        multiplier = TIME_UNIT_TO_SECONDS.get(unit, 3600)
        total_seconds = total_time * multiplier
        
        # Base delay per execution
        base_delay = total_seconds / executions
        
        # Generate random delays with jitter
        jitter_factor = jitter_percent / 100.0
        raw_delays = []
        
        for _ in range(executions):
            # Random value between (1 - jitter) and (1 + jitter) of base
            min_factor = 1 - jitter_factor
            max_factor = 1 + jitter_factor
            random_factor = random.uniform(min_factor, max_factor)
            raw_delays.append(base_delay * random_factor)
        
        # Normalize so sum equals exactly total_seconds
        raw_sum = sum(raw_delays)
        scale_factor = total_seconds / raw_sum
        normalized_delays = [d * scale_factor for d in raw_delays]
        
        return normalized_delays
    
    async def _get_or_create_delay_list(self) -> List[float]:
        """Get existing delay list from cache or create new one."""
        delays = await self.data_store.cache.get(self._cache_key)
        
        if not delays or len(delays) == 0:
            delays = self._generate_delay_list()
            await self._save_delay_list(delays)
            
            total_time = self.form.cleaned_data.get('total_time')
            unit = self.form.cleaned_data.get('unit')
            
            logger.info(
                "Generated new delay list",
                node_id=self.node_config.id,
                count=len(delays),
                target_time=f"{total_time} {unit}",
                actual_sum=self._format_duration(sum(delays)),
                min_delay=self._format_duration(min(delays)),
                max_delay=self._format_duration(max(delays)),
                delays_preview=[self._format_duration(d) for d in delays[:5]]
            )
        
        return delays
    
    async def _save_delay_list(self, delays: List[float]):
        """Save delay list to cache."""
        total_time = self.form.cleaned_data.get('total_time', 1)
        unit = self.form.cleaned_data.get('unit', 'hours')
        # TTL slightly longer than the max expected duration
        ttl = int(total_time * TIME_UNIT_TO_SECONDS.get(unit, 3600) * 1.5)
        await self.data_store.cache.set(self._cache_key, delays, ttl=ttl)
    
    async def _pop_next_delay(self) -> tuple:
        """
        Pop and return the next delay from the list.
        
        Returns:
            tuple: (next_delay_seconds, remaining_count)
        """
        delays = await self._get_or_create_delay_list()
        
        if len(delays) == 0:
            # List exhausted, generate new cycle
            delays = self._generate_delay_list()
            
            total_time = self.form.cleaned_data.get('total_time')
            unit = self.form.cleaned_data.get('unit')
            
            logger.info(
                "Regenerated delay list for new cycle",
                node_id=self.node_config.id,
                count=len(delays),
                target_time=f"{total_time} {unit}"
            )
        
        # Pop first delay
        next_delay = delays.pop(0)
        
        # Save remaining delays (or empty list)
        await self._save_delay_list(delays)
        
        return next_delay, len(delays)
    
    def _format_duration(self, seconds: float) -> str:
        """Format seconds into human-readable duration."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds / 60:.1f}m"
        elif seconds < 86400:
            return f"{seconds / 3600:.2f}h"
        else:
            return f"{seconds / 86400:.2f}d"
    
    async def execute(self, previous_node_output: NodeOutput) -> NodeOutput:
        """
        Execute by popping and applying the next pre-computed delay.
        
        Args:
            previous_node_output: The NodeOutput from the previous node.
            
        Returns:
            NodeOutput: The same data, passed through after the delay.
        """
        total_time = self.form.cleaned_data.get('total_time')
        unit = self.form.cleaned_data.get('unit')
        executions = self.form.cleaned_data.get('executions')
        
        # Get next delay from pre-computed list
        delay_seconds, remaining = await self._pop_next_delay()
        current_execution = executions - remaining
        
        logger.info(
            "Dynamic delay starting",
            node_id=self.node_config.id,
            execution=f"{current_execution}/{executions}",
            delay=self._format_duration(delay_seconds),
            remaining_in_list=remaining
        )
        
        # Apply the delay
        await asyncio.sleep(delay_seconds)
        
        # Log cycle completion
        if remaining == 0:
            logger.info(
                "Delay cycle complete - new list will be generated next execution",
                node_id=self.node_config.id,
                target_time=f"{total_time} {unit}"
            )
        
        logger.info(
            "Dynamic delay completed",
            node_id=self.node_config.id,
            waited=self._format_duration(delay_seconds)
        )
        
        return NodeOutput(
            id=previous_node_output.id,
            data=previous_node_output.data,
            metadata={
                "sourceNodeID": self.node_config.id,
                "sourceNodeName": self.node_config.type,
                "delayType": "dynamic_precomputed",
                "execution": f"{current_execution}/{executions}",
                "delayApplied": self._format_duration(delay_seconds),
                "delaySeconds": delay_seconds,
                "remainingInCycle": remaining
            }
        )


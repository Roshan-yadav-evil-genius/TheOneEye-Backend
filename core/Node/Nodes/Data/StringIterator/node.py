"""
StringIterator Node

Single Responsibility: Iterate over string data with configurable separators.
"""

from typing import Optional
import structlog

from ....Core.Node.Core import ProducerNode, NodeOutput, PoolType
from ....Core.Node.Core.Data import ExecutionCompleted
from ....Core.Form.Core.BaseForm import BaseForm
from .form import StringIteratorForm

logger = structlog.get_logger(__name__)


class StringIterator(ProducerNode):
    @classmethod
    def identifier(cls) -> str:
        return "string-iterator-producer"

    def get_form(self) -> Optional[BaseForm]:
        return StringIteratorForm()

    @property
    def execution_pool(self) -> PoolType:
        return PoolType.ASYNC

    async def setup(self):
        """
        Parse the data from the form configuration during setup.
        """
        form_data = self.node_config.data.form or {}
        raw_data = form_data.get("data_content", "")
        separator_type = form_data.get("separator_type", "newline")
        custom_separator = form_data.get("custom_separator", "")

        # Determine separator
        if separator_type == "newline":
            delimiter = "\n"
        elif separator_type == "comma":
            delimiter = ","
        elif separator_type == "custom" and custom_separator:
            delimiter = custom_separator
        else:
            delimiter = "\n" # Fallback

        if not raw_data:
            self.items = []
        else:
            # parsing logic
            self.items = [item.strip() for item in raw_data.split(delimiter) if item.strip()]
        
        self.current_index = 0
        logger.info("Initialized StringIterator", item_count=len(self.items))

    async def execute(self, node_data: NodeOutput) -> NodeOutput:
        """
        Yield the next item in the list.
        """
        if self.current_index >= len(self.items):
            logger.info("StringIterator finished", total_items=len(self.items))
            return ExecutionCompleted(
                id=self.node_config.id,
                data={"value": "Iteration completed"},
                metadata={
                    "sourceNodeID": self.node_config.id,
                    "__execution_completed__": True
                }
            )

        item = self.items[self.current_index]
        self.current_index += 1

        logger.info("Emitting item", index=self.current_index, item=item)

        output_key = self.get_unique_output_key(node_data, "string_iterator")
        node_data.data[output_key] = {
            "value": item,
            "iteration_index": self.current_index
        }
        return node_data


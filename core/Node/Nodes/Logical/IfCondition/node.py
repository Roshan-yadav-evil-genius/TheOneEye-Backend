"""
IfCondition Node

Single Responsibility: Evaluate conditional expressions for workflow branching.
"""

import structlog

from ....Core.Node.Core import ConditionalNode, NodeOutput, PoolType
from ....Core.Form import BaseForm
from .form import IfConditionForm

logger = structlog.get_logger(__name__)


class IfCondition(ConditionalNode):
    @classmethod
    def identifier(cls) -> str:
        return "if-condition"
    
    def get_form(self) -> BaseForm:
        return IfConditionForm()

    @property
    def execution_pool(self) -> PoolType:
        return PoolType.ASYNC

    async def execute(self, node_data: NodeOutput) -> NodeOutput:
        output_key = self.get_unique_output_key(node_data, "if_condition")

        # Get processed condition from form (rendered values)
        expression = self.form.cleaned_data.get("condition_expression", "")

        if not expression:
            logger.warning("No condition expression provided, defaulting to False", node_id=self.node_config.id)
            self.set_output(False)
            payload = {
                "route": self.output,
                "expression": "",
                "result": False
            }
            return NodeOutput(
                id=self.node_config.id,
                data={**node_data.data, output_key: payload},
                metadata=node_data.metadata
            )

        try:
            # Evaluate expression with 'data' in context
            # Using eval with restricted scope for basic safety
            context = {"data": node_data.data}
            result = eval(expression, {"__builtins__": {}}, context)
            
            # Ensure boolean result
            is_true = bool(result)
            
            logger.info(
                "Evaluated Condition", 
                expression=expression, 
                result=is_true, 
                node_id=self.node_config.id
            )
            
            self.set_output(is_true)
            
        except Exception as e:
            logger.error("Condition evaluation failed", error=str(e), expression=expression)
            raise ValueError(f"Failed to evaluate condition '{expression}': {str(e)}")

        payload = {
            "route": self.output,
            "expression": expression,
            "result": is_true
        }
        return NodeOutput(
            id=self.node_config.id,
            data={**node_data.data, output_key: payload},
            metadata=node_data.metadata
        )


"""
ForEachNode

Single Responsibility: Resolve the iteration array from one Jinja/JSON expression
and return a NodeOutput containing it; the runner performs subDAG iterations.
"""

import ast
import json
from typing import Any, List
import structlog

from ....Core.Node.Core import LoopNode, NodeOutput, PoolType
from ....Core.Form import BaseForm
from .form import ForEachNodeForm

logger = structlog.get_logger(__name__)


def _get_nested(data: dict, key: str) -> Any:
    """Get value from dict by key or dot path (e.g. 'items' or 'data.list')."""
    if not key or not data:
        return None
    parts = key.strip().split(".")
    current = data
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _ensure_list(value: Any) -> List[Any]:
    """Return value if it is a list, otherwise empty list."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return []


def _parse_expression_to_list(raw: str, node_data_data: dict) -> List[Any]:
    """
    Parse array_expression: already Jinja-rendered string, or key path.
    Tries: json.loads, ast.literal_eval, then key path into node_data_data.
    """
    raw = (raw or "").strip()
    if not raw:
        return []
    # Rendered Jinja often yields JSON or Python repr
    try:
        parsed = json.loads(raw)
        return _ensure_list(parsed)
    except (json.JSONDecodeError, TypeError):
        pass
    try:
        parsed = ast.literal_eval(raw)
        return _ensure_list(parsed)
    except (ValueError, SyntaxError):
        pass
    # Key path (e.g. "items" or "data.list")
    value = _get_nested(node_data_data, raw)
    return _ensure_list(value)


class ForEachNode(LoopNode):
    """
    Loop node: iterates over an array from one expression (Jinja or JSON),
    runs the subDAG once per element, collects end-node results, then continues.
    The runner performs iterations; execute() only resolves and returns the array.
    """

    @classmethod
    def identifier(cls) -> str:
        return "for-each"

    def get_form(self) -> BaseForm:
        return ForEachNodeForm()

    @property
    def execution_pool(self) -> PoolType:
        return PoolType.ASYNC

    async def execute(self, node_data: NodeOutput) -> NodeOutput:
        """
        Resolve the array from the single array_expression (Jinja-rendered or key path).
        Runner will iterate and run the subDAG; collected results use fixed key "loop_results".
        """
        form_data = self.form.cleaned_data or (self.node_config.data.form or {})
        raw = (form_data.get("array_expression") or "").strip()
        items = _parse_expression_to_list(raw, node_data.data)

        logger.info(
            "ForEach resolved array",
            node_id=self.node_config.id,
            count=len(items),
        )

        out_data = dict(node_data.data)
        out_data["items"] = items
        # No result_key: runner uses fixed "loop_results"

        return NodeOutput(
            id=node_data.id,
            data=out_data,
            metadata=node_data.metadata,
        )

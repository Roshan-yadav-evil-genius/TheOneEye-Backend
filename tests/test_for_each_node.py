"""
Unit tests for ForEachNode (Loop Node).
"""

import pytest
from Node.Core.Node.Core.Data import NodeConfig, NodeConfigData, NodeOutput
from Node.Nodes.Loop.ForEach.node import ForEachNode


def _make_config(form_data=None):
    return NodeConfig(
        id="test-loop-1",
        type="for-each",
        data=NodeConfigData(form=form_data or {}),
    )


@pytest.mark.asyncio
async def test_execute_returns_items_from_key_path():
    """ForEachNode.execute() resolves array from array_expression key path."""
    config = _make_config({"array_expression": "items"})
    node = ForEachNode(config)
    node_data = NodeOutput(data={"items": [1, 2, 3], "other": "keep"})
    result = await node.execute(node_data)
    assert result.data["items"] == [1, 2, 3]
    assert result.data.get("other") == "keep"


@pytest.mark.asyncio
async def test_execute_empty_expression_returns_empty_list():
    """ForEachNode.execute() with missing or empty expression returns empty items list."""
    config = _make_config({"array_expression": ""})
    node = ForEachNode(config)
    node_data = NodeOutput(data={})
    result = await node.execute(node_data)
    assert result.data["items"] == []


@pytest.mark.asyncio
async def test_execute_dot_path_array_key():
    """ForEachNode.execute() resolves nested key path from array_expression."""
    config = _make_config({"array_expression": "data.list"})
    node = ForEachNode(config)
    node_data = NodeOutput(data={"data": {"list": ["a", "b"]}})
    result = await node.execute(node_data)
    assert result.data["items"] == ["a", "b"]


@pytest.mark.asyncio
async def test_execute_parses_json_array_expression():
    """ForEachNode.execute() parses JSON array from rendered expression."""
    config = _make_config({"array_expression": '[1, 2, 3]'})
    node = ForEachNode(config)
    node_data = NodeOutput(data={})
    result = await node.execute(node_data)
    assert result.data["items"] == [1, 2, 3]

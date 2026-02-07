"""
Unit tests for fork-join merge helpers and key policy.
"""

import pytest

from core.Node.Core.Node.Core.Data import NodeOutput

from core.Workflow.execution.fork_join import get_unique_key, merge_branch_outputs


def test_get_unique_key_returns_base_key_when_missing():
    data = {}
    assert get_unique_key(data, "webpage_loader") == "webpage_loader"


def test_get_unique_key_returns_key_2_when_key_exists():
    data = {"webpage_loader": {}}
    assert get_unique_key(data, "webpage_loader") == "webpage_loader_2"


def test_get_unique_key_returns_key_3_when_key_2_exists():
    data = {"webpage_loader": {}, "webpage_loader_2": {}}
    assert get_unique_key(data, "webpage_loader") == "webpage_loader_3"


def test_merge_branch_outputs_combines_initial_and_all_branch_keys():
    initial = NodeOutput(data={"initial": 1}, id="id-1")
    branch_a = NodeOutput(data={"webpage_loader": {"url": "a"}}, id="id-1")
    branch_b = NodeOutput(data={"network_interceptor": {"requests": []}}, id="id-1")
    merged = merge_branch_outputs(initial, [branch_a, branch_b])
    assert merged.data["initial"] == 1
    assert merged.data["webpage_loader"] == {"url": "a"}
    assert merged.data["network_interceptor"] == {"requests": []}
    assert merged.id == "id-1"


def test_merge_branch_outputs_resolves_collisions_with_key_2():
    initial = NodeOutput(data={"initial": 1}, id="id-1")
    branch_a = NodeOutput(data={"webpage_loader": {"a": 1}}, id="id-1")
    branch_b = NodeOutput(data={"webpage_loader": {"b": 2}}, id="id-1")
    merged = merge_branch_outputs(initial, [branch_a, branch_b])
    assert merged.data["initial"] == 1
    assert merged.data["webpage_loader"] == {"a": 1}
    assert merged.data["webpage_loader_2"] == {"b": 2}


def test_merge_branch_outputs_empty_branch_outputs_returns_initial():
    initial = NodeOutput(data={"x": 1}, id="id-1")
    merged = merge_branch_outputs(initial, [])
    assert merged.data == {"x": 1}
    assert merged.id == "id-1"


def test_merge_branch_outputs_full_data_from_each_branch():
    """Join node receives every key from every branch (all node outputs)."""
    initial = NodeOutput(data={"pre": 0}, id="id-1")
    branch_a = NodeOutput(
        data={"a1": 1, "a2": 2, "a3": 3},
        id="id-1",
    )
    branch_b = NodeOutput(data={"b1": 10}, id="id-1")
    merged = merge_branch_outputs(initial, [branch_a, branch_b])
    assert merged.data["pre"] == 0
    assert merged.data["a1"] == 1
    assert merged.data["a2"] == 2
    assert merged.data["a3"] == 3
    assert merged.data["b1"] == 10

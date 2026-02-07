"""
Unit tests for dev mode merged input (_merge_upstream_outputs and get_node_input_payload).
"""

import pytest

from apps.workflow.models import WorkFlow, Node, Connection
from apps.workflow.services.node_execution_service import NodeExecutionService
from apps.workflow.services.dependency_service import DependencyService


@pytest.mark.django_db
def test_merge_upstream_outputs_no_upstream():
    """No upstream nodes: merged dict equals request input_data."""
    workflow = WorkFlow.objects.create(name="w", description="")
    target = Node.objects.create(workflow=workflow, node_type="data-transformer")
    input_data = {"initial": 1}
    merged = NodeExecutionService._merge_upstream_outputs(target, input_data)
    assert merged == {"initial": 1}


@pytest.mark.django_db
def test_merge_upstream_outputs_two_upstreams_different_keys():
    """Two upstreams with different keys: merged has both (webpage_loader, network_interceptor)."""
    workflow = WorkFlow.objects.create(name="w", description="")
    source_a = Node.objects.create(workflow=workflow, node_type="webpage-loader", output_data={"webpage_loader": {"url": "a"}})
    source_b = Node.objects.create(workflow=workflow, node_type="network-interceptor", output_data={"network_interceptor": {"requests": []}})
    target = Node.objects.create(workflow=workflow, node_type="data-transformer")
    Connection.objects.create(workflow=workflow, source_node=source_a, target_node=target)
    Connection.objects.create(workflow=workflow, source_node=source_b, target_node=target)
    input_data = {"pre": 0}
    merged = NodeExecutionService._merge_upstream_outputs(target, input_data)
    assert merged["pre"] == 0
    assert merged["webpage_loader"] == {"url": "a"}
    assert merged["network_interceptor"] == {"requests": []}


@pytest.mark.django_db
def test_merge_upstream_outputs_duplicate_key_skipped():
    """Two upstreams both write same key: only the first is added, duplicate is skipped."""
    workflow = WorkFlow.objects.create(name="w", description="")
    source_a = Node.objects.create(workflow=workflow, node_type="x", output_data={"webpage_loader": {"a": 1}})
    source_b = Node.objects.create(workflow=workflow, node_type="y", output_data={"webpage_loader": {"b": 2}})
    target = Node.objects.create(workflow=workflow, node_type="data-transformer")
    Connection.objects.create(workflow=workflow, source_node=source_a, target_node=target)
    Connection.objects.create(workflow=workflow, source_node=source_b, target_node=target)
    merged = NodeExecutionService._merge_upstream_outputs(target, {})
    assert merged["webpage_loader"] == {"a": 1}
    assert "webpage_loader_2" not in merged


@pytest.mark.django_db
def test_merge_upstream_outputs_upstream_empty_output_data():
    """Upstream with empty or missing output_data: no keys added for that upstream."""
    workflow = WorkFlow.objects.create(name="w", description="")
    source_a = Node.objects.create(workflow=workflow, node_type="x", output_data={})
    target = Node.objects.create(workflow=workflow, node_type="y")
    Connection.objects.create(workflow=workflow, source_node=source_a, target_node=target)
    merged = NodeExecutionService._merge_upstream_outputs(target, {"initial": 1})
    assert merged == {"initial": 1}


@pytest.mark.django_db
def test_merge_upstream_outputs_upstream_non_dict_output_data():
    """Upstream with non-dict output_data (e.g. list/None): treated as {}, no keys added."""
    workflow = WorkFlow.objects.create(name="w", description="")
    source_a = Node.objects.create(workflow=workflow, node_type="x")
    source_a.output_data = [1, 2, 3]  # JSONField can store list; we treat as {}
    source_a.save()
    target = Node.objects.create(workflow=workflow, node_type="y")
    Connection.objects.create(workflow=workflow, source_node=source_a, target_node=target)
    merged = NodeExecutionService._merge_upstream_outputs(target, {"initial": 1})
    assert merged == {"initial": 1}


@pytest.mark.django_db
def test_get_node_input_payload_merged_shape():
    """get_node_input_payload returns merged dict from upstream output_data (same shape as execution)."""
    workflow = WorkFlow.objects.create(name="w", description="")
    source_a = Node.objects.create(workflow=workflow, node_type="webpage-loader", output_data={"webpage_loader": {"x": 1}})
    source_b = Node.objects.create(workflow=workflow, node_type="network-interceptor", output_data={"network_interceptor": {"y": 2}})
    target = Node.objects.create(workflow=workflow, node_type="data-transformer")
    Connection.objects.create(workflow=workflow, source_node=source_a, target_node=target)
    Connection.objects.create(workflow=workflow, source_node=source_b, target_node=target)
    payload = DependencyService.get_node_input_payload(str(target.id))
    assert payload["webpage_loader"] == {"x": 1}
    assert payload["network_interceptor"] == {"y": 2}

"""
Unit tests for BatchCosineSimilarityScorer node.
"""

import pytest
from ....Core.Node.Core.Data import NodeConfig, NodeConfigData, NodeOutput
from .node import BatchCosineSimilarityScorer, _parse_records, _ensure_list_of_dicts


def test_ensure_list_of_dicts():
    """Only dict items are kept; non-dicts are dropped."""
    assert _ensure_list_of_dicts([{"a": 1}, {"b": 2}]) == [{"a": 1}, {"b": 2}]
    assert _ensure_list_of_dicts([{"a": 1}, "x", 3, {"b": 2}]) == [{"a": 1}, {"b": 2}]
    assert _ensure_list_of_dicts(None) == []
    assert _ensure_list_of_dicts("not a list") == []


def test_parse_records_json():
    """Parse records from JSON string."""
    raw = '[{"post_content": "hello"}, {"post_content": "world"}]'
    assert _parse_records(raw, {}) == [{"post_content": "hello"}, {"post_content": "world"}]


def test_parse_records_empty():
    """Empty or whitespace returns empty list."""
    assert _parse_records("", {}) == []
    assert _parse_records("   ", {}) == []


@pytest.mark.asyncio
async def test_batch_cosine_similarity_scorer_node_execute():
    """BatchCosineSimilarityScorer returns list of records with similarity_score."""
    config = NodeConfig(
        id="test-batch-cosine-1",
        type="batch-cosine-similarity-scorer",
        data=NodeConfigData(
            form={
                "query": "automotive manufacturing",
                "records": '[{"post_content": "cars and vehicles"}, {"post_content": "food and cooking"}]',
                "content_key": "post_content",
            }
        ),
    )
    node = BatchCosineSimilarityScorer(config)
    node_data = NodeOutput(data={})
    result = await node.run(node_data)

    output_key = "batch_cosine_similarity_scorer"
    assert output_key in result.data
    scored = result.data[output_key]
    assert isinstance(scored, list)
    assert len(scored) == 2
    assert all("similarity_score" in r and "post_content" in r for r in scored)
    assert 0 <= scored[0]["similarity_score"] <= 1
    assert 0 <= scored[1]["similarity_score"] <= 1
    # First record should be more similar to "automotive manufacturing" than second
    assert scored[0]["similarity_score"] >= scored[1]["similarity_score"]


@pytest.mark.asyncio
async def test_batch_cosine_similarity_scorer_empty_records():
    """Empty records returns empty list under output key."""
    config = NodeConfig(
        id="test-batch-cosine-2",
        type="batch-cosine-similarity-scorer",
        data=NodeConfigData(
            form={
                "query": "test",
                "records": "[]",
                "content_key": "body",
            }
        ),
    )
    node = BatchCosineSimilarityScorer(config)
    result = await node.run(NodeOutput(data={}))
    assert result.data["batch_cosine_similarity_scorer"] == []

"""
Unit tests for CosineSimilarity node and cosine similarity helper.
"""

import pytest
from Node.Core.Node.Core.Data import NodeConfig, NodeConfigData, NodeOutput
from Node.Nodes.Data.CosineSimilarity.node import CosineSimilarity, _cosine_similarity


def test_cosine_similarity_identical_strings():
    """Identical strings yield 1.0."""
    assert _cosine_similarity("hello world", "hello world") == 1.0


def test_cosine_similarity_empty_strings():
    """Empty or missing string yields 0.0."""
    assert _cosine_similarity("", "hello") == 0.0
    assert _cosine_similarity("hello", "") == 0.0
    assert _cosine_similarity("", "") == 0.0


def test_cosine_similarity_no_overlap():
    """No shared words yield 0.0."""
    assert _cosine_similarity("apple banana", "car dog") == 0.0


def test_cosine_similarity_partial_overlap():
    """Partial overlap yields value in (0, 1)."""
    s = _cosine_similarity("hello world", "hello there")
    assert 0 < s < 1


def test_cosine_similarity_case_insensitive():
    """Tokenization is case-insensitive (lowercased)."""
    assert _cosine_similarity("Hello World", "hello world") == 1.0


@pytest.mark.asyncio
async def test_cosine_similarity_node_execute():
    """CosineSimilarity node returns cosine_similarity in output."""
    config = NodeConfig(
        id="test-cosine-similarity-1",
        type="cosine-similarity",
        data=NodeConfigData(form={"data_1": "hello world", "data_2": "hello there"}),
    )
    node = CosineSimilarity(config)
    node_data = NodeOutput(data={})
    result = await node.run(node_data)
    assert "cosine_similarity" in result.data
    assert isinstance(result.data["cosine_similarity"], (int, float))
    assert 0 <= result.data["cosine_similarity"] <= 1


@pytest.mark.asyncio
async def test_cosine_similarity_node_identical():
    """CosineSimilarity node returns 1.0 for identical strings."""
    config = NodeConfig(
        id="test-cosine-similarity-2",
        type="cosine-similarity",
        data=NodeConfigData(form={"data_1": "same text", "data_2": "same text"}),
    )
    node = CosineSimilarity(config)
    result = await node.run(NodeOutput(data={}))
    assert result.data["cosine_similarity"] == 1.0

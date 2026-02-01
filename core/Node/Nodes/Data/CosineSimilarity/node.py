"""
CosineSimilarity Node

Single Responsibility: Compute cosine similarity between two strings using word-level term frequency.
"""

import math
from typing import Optional
import structlog

from ....Core.Node.Core import BlockingNode, NodeOutput, PoolType
from ....Core.Form import BaseForm
from .form import CosineSimilarityForm

logger = structlog.get_logger(__name__)


def _cosine_similarity(s1: str, s2: str) -> float:
    """
    Compute cosine similarity between two strings (word-level term frequency).

    Tokenizes by lowercasing and splitting on whitespace. Empty or zero-norm
    inputs return 0.0.
    """
    s1 = (s1 or "").strip()
    s2 = (s2 or "").strip()

    tokens1 = s1.lower().split() if s1 else []
    tokens2 = s2.lower().split() if s2 else []

    if not tokens1 or not tokens2:
        return 0.0

    # Term frequency vectors (dict: term -> count)
    def term_freq(tokens):
        counts = {}
        for t in tokens:
            counts[t] = counts.get(t, 0) + 1
        return counts

    vec1 = term_freq(tokens1)
    vec2 = term_freq(tokens2)

    vocab = set(vec1) | set(vec2)
    dot = sum(vec1.get(t, 0) * vec2.get(t, 0) for t in vocab)
    norm1 = math.sqrt(sum(x * x for x in vec1.values()))
    norm2 = math.sqrt(sum(x * x for x in vec2.values()))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    similarity = dot / (norm1 * norm2)
    return max(0.0, min(1.0, similarity))


class CosineSimilarity(BlockingNode):
    """
    Compute cosine similarity between two strings.

    Uses word-level term frequency vectors. Both strings are tokenized by
    lowercasing and splitting on whitespace. Output is in [0, 1].
    """

    @classmethod
    def identifier(cls) -> str:
        """Unique identifier for this node type."""
        return "cosine-similarity"

    @property
    def label(self) -> str:
        """Display name for UI."""
        return "Cosine Similarity"

    @property
    def description(self) -> str:
        """Node description for documentation."""
        return "Compute cosine similarity between two strings (word-level term frequency)"

    @property
    def icon(self) -> str:
        """Icon identifier for UI."""
        return "transform"

    def get_form(self) -> Optional[BaseForm]:
        """Return the configuration form."""
        return CosineSimilarityForm()

    @property
    def execution_pool(self) -> PoolType:
        """Use ASYNC pool - lightweight CPU work."""
        return PoolType.ASYNC

    async def execute(self, node_data: NodeOutput) -> NodeOutput:
        """
        Read Data 1 and Data 2 from form, compute cosine similarity, return result.
        """
        data_1 = self.form.cleaned_data.get("data_1") or ""
        data_2 = self.form.cleaned_data.get("data_2") or ""
        data_1 = str(data_1).strip()
        data_2 = str(data_2).strip()

        similarity = _cosine_similarity(data_1, data_2)

        logger.info(
            "Cosine similarity computed",
            node_id=self.node_config.id,
            similarity=similarity,
        )

        return NodeOutput(
            id=node_data.id,
            data={
                **node_data.data,
                "cosine_similarity": similarity,
            },
            metadata={
                "sourceNodeID": self.node_config.id,
                "sourceNodeName": self.node_config.type,
                "operation": "cosine_similarity",
            },
        )

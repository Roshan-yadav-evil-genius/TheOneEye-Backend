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
from langchain_chroma.vectorstores import cosine_similarity

from django.conf import settings


logger = structlog.get_logger(__name__)


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
        return (
            "Compute cosine similarity between two strings (word-level term frequency)"
        )

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

    async def init(self):
        """Initialize the embedding model (cached per process, thread-safe)."""
        from ..heavy_model_cache import get_or_load_sentence_transformer

        model_path = (settings.BASE_DIR / "bin" / "models" / "bge-large-en-v1.5").as_posix()
        self.embedding_model = get_or_load_sentence_transformer(model_path)

    async def execute(self, node_data: NodeOutput) -> NodeOutput:
        """
        Read Data 1 and Data 2 from form, compute cosine similarity, return result.
        """
        data_1 = self.form.cleaned_data.get("data_1") or ""
        data_2 = self.form.cleaned_data.get("data_2") or ""

        vec1 = self.embedding_model.encode(data_1,show_progress_bar=False,normalize_embeddings=True)
        vec2 = self.embedding_model.encode(data_2,show_progress_bar=False,normalize_embeddings=True)

        similarity = cosine_similarity([vec1], [vec2])[0, 0]

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

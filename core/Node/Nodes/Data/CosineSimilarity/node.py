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
        """Initialize the embedding model."""
        from langchain_huggingface import HuggingFaceEmbeddings

        self.embedding_model = HuggingFaceEmbeddings(
            model_name="BAAI/bge-large-en-v1.5",
            # model_name="BAAI/bge-small-en-v1.5",
            cache_folder=(settings.BASE_DIR / "bin" / "huggingface_cache").as_posix(),
        )

    async def execute(self, node_data: NodeOutput) -> NodeOutput:
        """
        Read Data 1 and Data 2 from form, compute cosine similarity, return result.
        """
        data_1 = self.form.cleaned_data.get("data_1") or ""
        data_2 = self.form.cleaned_data.get("data_2") or ""

        vec1 = self.embedding_model.embed_query(data_1)
        vec2 = self.embedding_model.embed_query(data_2)

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

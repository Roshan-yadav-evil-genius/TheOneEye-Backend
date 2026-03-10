"""
CrossEncoder Node

Single Responsibility: Compute a relevance score between two texts using a cross-encoder (bge-reranker-large).
"""

from typing import Optional
import structlog

from ....Core.Node.Core import BlockingNode, NodeOutput, PoolType
from ....Core.Form import BaseForm
from .form import CrossEncoderForm

from django.conf import settings


logger = structlog.get_logger(__name__)


class CrossEncoder(BlockingNode):
    """
    Compute relevance score between two texts using a cross-encoder.
    Uses bge-reranker-large; output is a single float score (higher = more relevant).
    """

    @classmethod
    def identifier(cls) -> str:
        """Unique identifier for this node type."""
        return "cross-encoder"

    @property
    def label(self) -> str:
        """Display name for UI."""
        return "Cross Encoder"

    @property
    def description(self) -> str:
        """Node description for documentation."""
        return "Compute relevance score between two texts using a cross-encoder (bge-reranker-large)."

    @property
    def icon(self) -> str:
        """Icon identifier for UI."""
        return "transform"

    def get_form(self) -> Optional[BaseForm]:
        """Return the configuration form."""
        return CrossEncoderForm()

    @property
    def execution_pool(self) -> PoolType:
        """Use ASYNC pool - CPU-bound cross-encoder inference."""
        return PoolType.ASYNC

    async def init(self):
        """Initialize the cross-encoder model (cached per process, thread-safe)."""
        from ..heavy_model_cache import get_or_load_cross_encoder

        model_path = (settings.BASE_DIR / "bin" / "models" / "bge-reranker-large").as_posix()
        self.cross_encoder = get_or_load_cross_encoder(model_path)

    async def execute(self, node_data: NodeOutput) -> NodeOutput:
        """
        Read text_1 and text_2 from form, run cross-encoder predict, return score.
        """
        text_1 = self.form.cleaned_data.get("text_1") or ""
        text_2 = self.form.cleaned_data.get("text_2") or ""

        scores = self.cross_encoder.predict([[text_1, text_2]])
        score = float(scores[0])

        logger.info(
            "CrossEncoder score computed",
            node_id=self.node_config.id,
            score=score,
        )

        output_key = self.get_unique_output_key(node_data, "cross_encoder_score")

        return NodeOutput(
            id=node_data.id,
            data={
                **(node_data.data or {}),
                output_key: score,
            },
            metadata={
                "sourceNodeID": self.node_config.id,
                "sourceNodeName": self.node_config.type,
                "operation": "cross_encoder",
            },
        )

"""
BatchCosineSimilarityScorer Node

Single Responsibility: Score a list of records by cosine similarity of embeddings to a query.
"""

import ast
import json
from typing import Any, List, Optional
import structlog

from ....Core.Node.Core import BlockingNode, NodeOutput, PoolType
from ....Core.Form import BaseForm
from .form import BatchCosineSimilarityScorerForm
from django.conf import settings
from langchain_chroma.vectorstores import cosine_similarity


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


def _ensure_list_of_dicts(value: Any) -> List[dict]:
    """Return value if it is a list of dicts; coerce or skip non-dict items; otherwise empty list."""
    if value is None:
        return []
    if not isinstance(value, list):
        return []
    return [x for x in value if isinstance(x, dict)]


def _parse_records(raw: str, node_data_data: dict) -> List[dict]:
    """
    Parse records: Jinja-rendered JSON/Python or key path into node_data.data.
    Returns list of dicts.
    """
    raw = (raw or "").strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        return _ensure_list_of_dicts(parsed)
    except (json.JSONDecodeError, TypeError):
        pass
    try:
        parsed = ast.literal_eval(raw)
        return _ensure_list_of_dicts(parsed)
    except (ValueError, SyntaxError):
        pass
    value = _get_nested(node_data_data, raw)
    return _ensure_list_of_dicts(value) if value is not None else []


class BatchCosineSimilarityScorer(BlockingNode):
    """
    Score records by cosine similarity to a query using embeddings.
    Each record is a dict; the text to embed is taken from record[content_key].
    """

    @classmethod
    def identifier(cls) -> str:
        return "batch-cosine-similarity-scorer"

    @property
    def label(self) -> str:
        return "Batch Cosine Similarity Scorer"

    @property
    def description(self) -> str:
        return "Score records by cosine similarity to query using embeddings"

    @property
    def icon(self) -> str:
        return "transform"

    def get_form(self) -> Optional[BaseForm]:
        return BatchCosineSimilarityScorerForm()

    @property
    def execution_pool(self) -> PoolType:
        return PoolType.ASYNC

    async def init(self):
        """Initialize the embedding model (cached per process, thread-safe)."""
        from ..heavy_model_cache import get_or_load_sentence_transformer

        model_path = (settings.BASE_DIR / "bin" / "models" / "bge-large-en-v1.5").as_posix()
        self.embedding_model = get_or_load_sentence_transformer(model_path)

    async def execute(self, node_data: NodeOutput) -> NodeOutput:
        query = self.form.cleaned_data["query"]
        records_raw = self.form.cleaned_data["records"]
        content_key = self.form.cleaned_data["content_key"]

        records = _parse_records(records_raw, node_data.data or {})

        if not records:
            output_key = self.get_unique_output_key(node_data, "batch_cosine_similarity_scorer")
            output_data = {**(node_data.data or {}), output_key: []}
            return NodeOutput(
                id=node_data.id,
                data=output_data,
                metadata={
                    "sourceNodeID": self.node_config.id,
                    "sourceNodeName": self.node_config.type,
                    "operation": "batch_cosine_similarity_scorer",
                },
            )

        query_vec = self.embedding_model.encode(query or "",show_progress_bar=False,normalize_embeddings=True)
        scored_records: List[dict] = []

        for record in records:
            text = (record.get(content_key) if isinstance(record.get(content_key), str) else "") or ""
            vec = self.embedding_model.encode(text,show_progress_bar=False,normalize_embeddings=True)
            score = float(cosine_similarity([query_vec], [vec])[0, 0])
            scored_records.append({**record, "similarity_score": score})

        # sort scored_records by similarity_score in descending order
        scored_records.sort(key=lambda x: x["similarity_score"], reverse=True)

        logger.info(
            "Batch cosine similarity computed",
            node_id=self.node_config.id,
            record_count=len(scored_records),
        )

        output_key = self.get_unique_output_key(node_data, "batch_cosine_similarity_scorer")
        output_data = {**(node_data.data or {}), output_key: scored_records}

        return NodeOutput(
            id=node_data.id,
            data=output_data,
            metadata={
                "sourceNodeID": self.node_config.id,
                "sourceNodeName": self.node_config.type,
                "operation": "batch_cosine_similarity_scorer",
            },
        )

"""
Heavy model cache for API workflow nodes.

Caches CrossEncoder and SentenceTransformer instances by model path so they are
loaded once per process and reused across all API workflow runs. Thread-safe for
concurrent workflow execution via a single threading.Lock around get-or-load.
"""

import threading
from typing import Any, Dict

import structlog

logger = structlog.get_logger(__name__)

_cross_encoder_cache: Dict[str, Any] = {}
_sentence_transformer_cache: Dict[str, Any] = {}
_lock = threading.Lock()


def get_or_load_cross_encoder(model_path: str) -> Any:
    """
    Return a cached CrossEncoder for model_path, or load and cache it.
    Thread-safe; concurrent first loads for the same path will not double-load.
    """
    with _lock:
        if model_path in _cross_encoder_cache:
            return _cross_encoder_cache[model_path]
        from sentence_transformers import CrossEncoder as STCrossEncoder

        logger.info("Loading and caching CrossEncoder", model_path=model_path)
        _cross_encoder_cache[model_path] = STCrossEncoder(model_path)
        return _cross_encoder_cache[model_path]


def get_or_load_sentence_transformer(model_path: str) -> Any:
    """
    Return a cached SentenceTransformer for model_path, or load and cache it.
    Thread-safe; concurrent first loads for the same path will not double-load.
    """
    with _lock:
        if model_path in _sentence_transformer_cache:
            return _sentence_transformer_cache[model_path]
        from sentence_transformers import SentenceTransformer

        logger.info("Loading and caching SentenceTransformer", model_path=model_path)
        _sentence_transformer_cache[model_path] = SentenceTransformer(model_path)
        return _sentence_transformer_cache[model_path]

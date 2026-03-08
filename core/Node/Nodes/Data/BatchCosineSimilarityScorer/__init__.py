"""
BatchCosineSimilarityScorer Node Package

Score a list of records by cosine similarity of embeddings to a query.
"""

from .node import BatchCosineSimilarityScorer
from .form import BatchCosineSimilarityScorerForm

__all__ = ["BatchCosineSimilarityScorer", "BatchCosineSimilarityScorerForm"]

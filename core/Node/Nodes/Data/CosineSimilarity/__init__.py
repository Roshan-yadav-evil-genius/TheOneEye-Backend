"""
CosineSimilarity Node Package

Provides cosine similarity computation between two strings (word-level term frequency).
"""

from .node import CosineSimilarity
from .form import CosineSimilarityForm

__all__ = ["CosineSimilarity", "CosineSimilarityForm"]

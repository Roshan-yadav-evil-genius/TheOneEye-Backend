"""
CrossEncoder Node Package

Single Responsibility: Compute relevance score between two texts using a cross-encoder.
"""

from .node import CrossEncoder
from .form import CrossEncoderForm

__all__ = ["CrossEncoder", "CrossEncoderForm"]

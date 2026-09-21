"""Portable author-voice profiling and adversarial evaluation primitives."""

from .corpus import split_items
from .distance import candidate_typicality, style_distance
from .lineup import Document, build_lineup, select_matched_controls
from .measure import measure_text, profile_documents

__all__ = [
    "Document",
    "build_lineup",
    "candidate_typicality",
    "measure_text",
    "profile_documents",
    "select_matched_controls",
    "split_items",
    "style_distance",
]

__version__ = "0.1.0"

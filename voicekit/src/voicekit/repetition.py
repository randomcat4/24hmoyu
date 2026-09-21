from __future__ import annotations

import re
import statistics
from collections import Counter
from typing import Sequence

from .measure import words


def ngram_set(text: str, n: int = 4) -> set[tuple[str, ...]]:
    toks = [w.lower() for w in words(text)]
    return {tuple(toks[i : i + n]) for i in range(len(toks) - n + 1)}


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


def audit_documents(texts: Sequence[str]) -> dict:
    grams = [ngram_set(t, 4) for t in texts]
    pairwise = [
        jaccard(grams[i], grams[j])
        for i in range(len(grams))
        for j in range(i + 1, len(grams))
    ]
    heads = [" ".join(w.lower() for w in words(t)[:6]) for t in texts if words(t)]
    duplicate_heads = {head: count for head, count in Counter(heads).items() if count > 1}
    return {
        "documents": len(texts),
        "mean_pairwise_4gram_overlap": round(statistics.mean(pairwise), 6) if pairwise else 0.0,
        "max_pairwise_4gram_overlap": round(max(pairwise), 6) if pairwise else 0.0,
        "duplicate_opening_heads": duplicate_heads,
    }


def audit_sections(text: str) -> dict:
    parts = [p.strip() for p in re.split(r"(?m)^#{1,6}\s+.+$", text) if len(words(p)) >= 30]
    return audit_documents(parts)

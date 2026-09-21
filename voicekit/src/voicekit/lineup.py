from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Sequence

from .measure import words


@dataclass(frozen=True, slots=True)
class Document:
    id: str
    text: str
    mode: str | None = None
    register: str | None = None
    era: str | None = None

    @property
    def word_count(self) -> int:
        return len(words(self.text))


def match_cost(target: Document, candidate: Document) -> float:
    """Cost for selecting a real control that matches the fake's observable context."""
    cost = abs(math.log((candidate.word_count + 1) / (target.word_count + 1)))
    if target.mode and candidate.mode and target.mode != candidate.mode:
        cost += 1.5
    if target.register and candidate.register and target.register != candidate.register:
        cost += 1.5
    if target.era and candidate.era and target.era != candidate.era:
        cost += 0.5
    return cost


def select_matched_controls(
    target: Document,
    candidates: Sequence[Document],
    *,
    n: int = 7,
) -> list[Document]:
    pool = [doc for doc in candidates if doc.id != target.id]
    if len(pool) < n:
        raise ValueError(f"need at least {n} real controls, got {len(pool)}")
    ranked = sorted(pool, key=lambda doc: (match_cost(target, doc), doc.id))
    return ranked[:n]


def build_lineup(
    fake: Document,
    real_candidates: Sequence[Document],
    *,
    n_controls: int = 7,
    seed: int = 42,
) -> tuple[str, dict]:
    controls = select_matched_controls(fake, real_candidates, n=n_controls)
    rows = [(fake, True), *((doc, False) for doc in controls)]
    rng = random.Random(seed)
    rng.shuffle(rows)
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if len(rows) > len(alphabet):
        raise ValueError("lineup too large")

    fake_label = ""
    sections = [
        "# Blind author-voice lineup",
        "",
        f"Exactly one of these {len(rows)} texts is synthetic. Guess which one. Do not assume the oddest topic or length is synthetic; controls were selected to match observable context.",
        "",
    ]
    labels: dict[str, str] = {}
    for index, (doc, is_fake) in enumerate(rows):
        label = alphabet[index]
        labels[label] = doc.id
        if is_fake:
            fake_label = label
        sections.extend([f"## TEXT {label}", "", doc.text.strip(), ""])
    key = {
        "fake_label": fake_label,
        "fake_id": fake.id,
        "labels": labels,
        "control_ids": [doc.id for doc in controls],
        "seed": seed,
    }
    return "\n".join(sections).strip() + "\n", key

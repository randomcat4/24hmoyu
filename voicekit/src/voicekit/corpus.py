from __future__ import annotations

import random
from pathlib import Path
from typing import Iterable, Sequence, TypeVar

T = TypeVar("T")


def split_items(
    items: Sequence[T],
    *,
    profile_ratio: float = 0.6,
    dev_ratio: float = 0.2,
    seed: int = 42,
) -> dict[str, list[T]]:
    """Deterministically split items into profile/dev/final holdouts.

    The function is deliberately domain-agnostic: callers can pass paths, IDs, or
    richer objects. No knowledge of the host application's corpus or ledger model
    is required.
    """
    if not 0 < profile_ratio < 1:
        raise ValueError("profile_ratio must be between 0 and 1")
    if not 0 <= dev_ratio < 1:
        raise ValueError("dev_ratio must be between 0 and 1")
    if profile_ratio + dev_ratio >= 1:
        raise ValueError("profile_ratio + dev_ratio must be < 1")

    rows = list(items)
    rng = random.Random(seed)
    rng.shuffle(rows)
    n = len(rows)
    if n == 0:
        return {"profile": [], "dev": [], "final": []}

    profile_n = max(1, round(n * profile_ratio))
    dev_n = round(n * dev_ratio)
    if n >= 3:
        dev_n = max(1, dev_n)
    if profile_n + dev_n >= n and n >= 2:
        overflow = profile_n + dev_n - (n - 1)
        profile_n = max(1, profile_n - overflow)

    return {
        "profile": rows[:profile_n],
        "dev": rows[profile_n : profile_n + dev_n],
        "final": rows[profile_n + dev_n :],
    }


def discover_text_files(
    root: str | Path,
    *,
    suffixes: Iterable[str] = (".md", ".txt"),
) -> list[Path]:
    root = Path(root)
    allowed = {s.lower() for s in suffixes}
    if not root.exists():
        raise FileNotFoundError(root)
    return sorted(
        p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in allowed
    )

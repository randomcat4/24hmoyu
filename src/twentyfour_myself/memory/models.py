from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class MemoryAction(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class MemoryKind(StrEnum):
    FACT = "fact"
    PROJECT = "project"
    DECISION = "decision"
    PREFERENCE = "preference"
    RESPONSIBILITY = "responsibility"
    BLOCKER = "blocker"
    RELATIONSHIP = "relationship"
    PROCEDURE = "procedure"
    OTHER = "other"


@dataclass(slots=True)
class MemoryItem:
    id: str
    kind: str
    content: str
    source_refs: list[str] = field(default_factory=list)
    confidence: float = 1.0
    importance: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None


@dataclass(slots=True)
class MemoryOperation:
    action: MemoryAction
    id: str | None = None
    kind: str | None = None
    content: str | None = None
    source_refs: list[str] = field(default_factory=list)
    confidence: float = 1.0
    importance: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)
    reason: str = ""

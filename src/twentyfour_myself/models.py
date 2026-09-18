from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import IntEnum, StrEnum
from typing import Any, Mapping, TypeAlias


class AuthorizationTier(IntEnum):
    """Authorization boundary required for a capability."""

    USER_FILE = 0
    USER_DELEGATED = 1
    ADMIN_APPROVED = 2


class RecordKind(StrEnum):
    MESSAGE = "message"
    DOCUMENT = "document"
    ATTACHMENT = "attachment"


@dataclass(frozen=True, slots=True)
class Capability:
    name: str
    supported: bool
    auth_tier: AuthorizationTier
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "supported": self.supported,
            "auth_tier": int(self.auth_tier),
            "notes": self.notes,
        }


@dataclass(slots=True)
class BaseRecord:
    source: str
    external_id: str
    collected_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def kind(self) -> RecordKind:
        raise NotImplementedError

    @property
    def stable_key(self) -> str:
        return f"{self.source}:{self.kind.value}:{self.external_id}"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["kind"] = self.kind.value
        return data


@dataclass(slots=True)
class Message(BaseRecord):
    channel_id: str | None = None
    sender_id: str | None = None
    sender_name: str | None = None
    timestamp: str | None = None
    text: str = ""
    attachment_refs: list[str] = field(default_factory=list)

    @property
    def kind(self) -> RecordKind:
        return RecordKind.MESSAGE


@dataclass(slots=True)
class Document(BaseRecord):
    title: str = ""
    content: str = ""
    owner_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    attachment_refs: list[str] = field(default_factory=list)

    @property
    def kind(self) -> RecordKind:
        return RecordKind.DOCUMENT


@dataclass(slots=True)
class Attachment(BaseRecord):
    filename: str = ""
    mime_type: str | None = None
    size: int | None = None
    local_path: str | None = None
    parent_ref: str | None = None

    @property
    def kind(self) -> RecordKind:
        return RecordKind.ATTACHMENT


Record: TypeAlias = Message | Document | Attachment


def record_from_dict(data: Mapping[str, Any]) -> Record:
    payload = dict(data)
    kind = RecordKind(payload.pop("kind"))
    if kind is RecordKind.MESSAGE:
        return Message(**payload)
    if kind is RecordKind.DOCUMENT:
        return Document(**payload)
    if kind is RecordKind.ATTACHMENT:
        return Attachment(**payload)
    raise ValueError(f"Unsupported record kind: {kind}")

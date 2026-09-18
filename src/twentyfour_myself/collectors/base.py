from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from ..models import Capability, Record


class CollectorError(RuntimeError):
    pass


class AuthorizationRequired(CollectorError):
    pass


class CapabilityUnavailable(CollectorError):
    pass


@dataclass(slots=True)
class CollectorContext:
    output_dir: Path

    @property
    def attachments_dir(self) -> Path:
        path = self.output_dir / "attachments"
        path.mkdir(parents=True, exist_ok=True)
        return path


class BaseCollector(ABC):
    source: str

    @abstractmethod
    def capabilities(self) -> list[Capability]:
        raise NotImplementedError

    @abstractmethod
    def collect(self, context: CollectorContext) -> Iterable[Record]:
        raise NotImplementedError

    def capability(self, name: str) -> Capability:
        for item in self.capabilities():
            if item.name == name:
                return item
        raise KeyError(name)

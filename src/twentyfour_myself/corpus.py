from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator

from .models import Record, record_from_dict


@dataclass(slots=True)
class CorpusStats:
    added: int = 0
    duplicates: int = 0


class CorpusStore:
    """Simple local JSONL corpus with deterministic de-duplication.

    The store never writes raw API credentials. Attachments are expected to be
    written below ``attachments/`` by collectors and referenced from records.
    """

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.records_path = self.root / "records.jsonl"
        self.manifest_path = self.root / "manifest.json"
        self.attachments_dir = self.root / "attachments"

    def initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.attachments_dir.mkdir(parents=True, exist_ok=True)
        if not self.records_path.exists():
            self.records_path.touch()

    def iter_records(self) -> Iterator[Record]:
        if not self.records_path.exists():
            return
        with self.records_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    yield record_from_dict(json.loads(line))

    def _existing_keys(self) -> set[str]:
        return {record.stable_key for record in self.iter_records()}

    def append(self, records: Iterable[Record]) -> CorpusStats:
        self.initialize()
        existing = self._existing_keys()
        stats = CorpusStats()
        with self.records_path.open("a", encoding="utf-8") as fh:
            for record in records:
                if record.stable_key in existing:
                    stats.duplicates += 1
                    continue
                fh.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
                existing.add(record.stable_key)
                stats.added += 1
        self._write_manifest()
        return stats

    def _write_manifest(self) -> None:
        counts = {"message": 0, "document": 0, "attachment": 0}
        sources: set[str] = set()
        for record in self.iter_records():
            counts[record.kind.value] += 1
            sources.add(record.source)
        manifest = {
            "schema_version": 1,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "record_counts": counts,
            "sources": sorted(sources),
        }
        self._atomic_json_write(self.manifest_path, manifest)

    @staticmethod
    def _atomic_json_write(path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=path.name, dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
                fh.write("\n")
            os.replace(tmp_name, path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

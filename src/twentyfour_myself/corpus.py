from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator

from .models import Attachment, Document, Message, Record, record_from_dict


@dataclass(slots=True)
class CorpusStats:
    added: int = 0
    updated: int = 0
    duplicates: int = 0


def _record_fingerprint(record: Record) -> str:
    payload = record.to_dict()
    payload.pop("collected_at", None)
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _record_time(record: Record) -> str | None:
    if isinstance(record, Message):
        return record.timestamp or record.collected_at
    if isinstance(record, Document):
        return (
            record.updated_at
            or record.created_at
            or record.collected_at
        )
    if isinstance(record, Attachment):
        return record.collected_at
    return record.collected_at


class CorpusStore:
    """Append-only local experience log with latest-state views.

    The raw JSONL is the durable experience stream. Re-collecting the same
    stable key with changed content appends a revision instead of silently
    discarding it. Exact repeats are ignored.
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
        try:
            os.chmod(self.root, 0o700)
            os.chmod(self.attachments_dir, 0o700)
            os.chmod(self.records_path, 0o600)
        except OSError:
            pass

    def iter_events(self) -> Iterator[Record]:
        if not self.records_path.exists():
            return
        with self.records_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    yield record_from_dict(json.loads(line))

    def iter_records(self) -> Iterator[Record]:
        latest: dict[str, Record] = {}
        for record in self.iter_events():
            latest[record.stable_key] = record
        yield from latest.values()

    def _latest_fingerprints(self) -> dict[str, str]:
        latest: dict[str, str] = {}
        for record in self.iter_events():
            latest[record.stable_key] = _record_fingerprint(record)
        return latest

    def append(self, records: Iterable[Record]) -> CorpusStats:
        self.initialize()
        latest = self._latest_fingerprints()
        stats = CorpusStats()
        with self.records_path.open("a", encoding="utf-8") as fh:
            for record in records:
                fingerprint = _record_fingerprint(record)
                previous = latest.get(record.stable_key)
                if previous == fingerprint:
                    stats.duplicates += 1
                    continue
                fh.write(
                    json.dumps(
                        record.to_dict(),
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                if previous is None:
                    stats.added += 1
                else:
                    stats.updated += 1
                latest[record.stable_key] = fingerprint
        self._write_manifest()
        return stats

    def read_events_from(
        self,
        offset: int = 0,
        *,
        limit: int | None = None,
    ) -> tuple[list[Record], int]:
        self.initialize()
        size = self.records_path.stat().st_size
        if offset < 0 or offset > size:
            raise ValueError(
                f"invalid corpus offset {offset}; file size is {size}"
            )

        records: list[Record] = []
        with self.records_path.open("rb") as fh:
            fh.seek(offset)
            while limit is None or len(records) < limit:
                line = fh.readline()
                if not line:
                    break
                if not line.strip():
                    continue
                records.append(
                    record_from_dict(
                        json.loads(line.decode("utf-8"))
                    )
                )
            return records, fh.tell()

    def query(
        self,
        *,
        since: str | None = None,
        until: str | None = None,
        source: str | None = None,
        kind: str | None = None,
        text: str | None = None,
        latest_only: bool = True,
    ) -> Iterator[Record]:
        rows = (
            self.iter_records()
            if latest_only
            else self.iter_events()
        )
        needle = text.casefold() if text else None

        for record in rows:
            if source and record.source != source:
                continue
            if kind and record.kind.value != kind:
                continue

            ts = _record_time(record)
            if since and ts and ts < since:
                continue
            if until and ts and ts > until:
                continue

            if needle:
                haystack = json.dumps(
                    record.to_dict(),
                    ensure_ascii=False,
                ).casefold()
                if needle not in haystack:
                    continue

            yield record

    def _write_manifest(self) -> None:
        counts = {
            "message": 0,
            "document": 0,
            "attachment": 0,
        }
        sources: set[str] = set()
        current = list(self.iter_records())

        for record in current:
            counts[record.kind.value] += 1
            sources.add(record.source)

        manifest = {
            "schema_version": 2,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "record_counts": counts,
            "event_count": sum(1 for _ in self.iter_events()),
            "sources": sorted(sources),
        }
        self._atomic_json_write(
            self.manifest_path,
            manifest,
        )

    @staticmethod
    def _atomic_json_write(path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            prefix=path.name,
            dir=path.parent,
        )
        try:
            with os.fdopen(
                fd,
                "w",
                encoding="utf-8",
            ) as fh:
                json.dump(
                    payload,
                    fh,
                    ensure_ascii=False,
                    indent=2,
                )
                fh.write("\n")
            os.replace(tmp_name, path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

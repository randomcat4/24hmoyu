from __future__ import annotations

# The create/update/delete validation semantics in _apply_operation are adapted from
# langchain-ai/langmem (MIT), Copyright (c) 2025 LangChain.

import json
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .models import MemoryAction, MemoryItem, MemoryOperation


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryStore:
    def __init__(self, corpus_root: str | Path):
        self.root = Path(corpus_root)
        self.path = self.root / "memory.sqlite3"

    def initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source_refs TEXT NOT NULL DEFAULT '[]',
                    confidence REAL NOT NULL DEFAULT 1.0,
                    importance REAL NOT NULL DEFAULT 0.5,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    deleted_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_memories_active_updated
                    ON memories(deleted_at, updated_at DESC);
                CREATE TABLE IF NOT EXISTS memory_events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    before_json TEXT,
                    after_json TEXT,
                    run_id TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS dream_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
        try:
            os.chmod(self.root, 0o700)
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def list(self, *, include_deleted: bool = False, limit: int = 200) -> list[MemoryItem]:
        self.initialize()
        where = "" if include_deleted else "WHERE deleted_at IS NULL"
        with self._connect() as db:
            rows = db.execute(
                f"SELECT * FROM memories {where} ORDER BY importance DESC, updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_item(row) for row in rows]

    def get(self, memory_id: str) -> MemoryItem | None:
        self.initialize()
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM memories WHERE id = ? AND deleted_at IS NULL",
                (memory_id,),
            ).fetchone()
        return self._row_to_item(row) if row else None

    def search(self, query: str, *, limit: int = 10) -> list[MemoryItem]:
        self.initialize()
        query = query.strip().casefold()
        if not query:
            return self.list(limit=limit)
        terms = re.findall(r"[a-z0-9_./+-]{2,}|[\u4e00-\u9fff]{2,}", query)[:12]
        if not terms:
            terms = [query]
        clauses = " OR ".join("lower(content) LIKE ?" for _ in terms)
        params = [f"%{term}%" for term in terms]
        with self._connect() as db:
            rows = db.execute(
                f"""
                SELECT * FROM memories
                WHERE deleted_at IS NULL AND ({clauses})
                ORDER BY importance DESC, updated_at DESC
                LIMIT ?
                """,
                (*params, limit),
            ).fetchall()
        return [self._row_to_item(row) for row in rows]

    def get_state(self, key: str, default: str | None = None) -> str | None:
        self.initialize()
        with self._connect() as db:
            row = db.execute(
                "SELECT value FROM dream_state WHERE key = ?",
                (key,),
            ).fetchone()
        return row["value"] if row else default

    def set_state(self, key: str, value: str) -> None:
        self.initialize()
        now = _now()
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO dream_state(key, value, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE
                SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (key, value, now),
            )

    def apply_operations(
        self,
        operations: list[MemoryOperation],
        *,
        run_id: str | None = None,
    ) -> list[MemoryItem]:
        self.initialize()
        changed: list[MemoryItem] = []
        with self._connect() as db:
            for op in operations:
                item = self._apply_operation(db, op, run_id=run_id)
                if item is not None:
                    changed.append(item)
        return changed

    def commit_dream(
        self,
        operations: list[MemoryOperation],
        *,
        checkpoint_key: str,
        checkpoint_value: str,
        run_id: str,
    ) -> list[MemoryItem]:
        """Apply a dream batch and advance its checkpoint atomically."""
        self.initialize()
        changed: list[MemoryItem] = []
        now = _now()
        with self._connect() as db:
            for op in operations:
                item = self._apply_operation(db, op, run_id=run_id)
                if item is not None:
                    changed.append(item)
            db.execute(
                """
                INSERT INTO dream_state(key, value, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE
                SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (checkpoint_key, checkpoint_value, now),
            )
        return changed

    def _apply_operation(
        self,
        db: sqlite3.Connection,
        op: MemoryOperation,
        *,
        run_id: str | None,
    ) -> MemoryItem | None:
        if op.action is MemoryAction.CREATE and op.id is not None:
            raise ValueError("create must not provide a memory id")
        if op.action in (MemoryAction.UPDATE, MemoryAction.DELETE) and not op.id:
            raise ValueError(f"{op.action.value} requires a memory id")

        now = _now()
        before = None
        if op.id:
            before = db.execute(
                "SELECT * FROM memories WHERE id = ?",
                (op.id,),
            ).fetchone()

        if op.action is MemoryAction.DELETE:
            if before is None or before["deleted_at"] is not None:
                return None
            db.execute(
                "UPDATE memories SET deleted_at = ?, updated_at = ? WHERE id = ?",
                (now, now, op.id),
            )
            self._log_event(db, op.id, op.action.value, before, None, run_id, now)
            return None

        if not op.content or not op.content.strip():
            raise ValueError(f"{op.action.value} requires non-empty content")

        kind = (op.kind or (before["kind"] if before else "other")).strip()
        source_refs = list(dict.fromkeys(op.source_refs))
        confidence = max(0.0, min(float(op.confidence), 1.0))
        importance = max(0.0, min(float(op.importance), 1.0))
        metadata = op.metadata or {}

        if op.action is MemoryAction.CREATE:
            duplicate = db.execute(
                """
                SELECT * FROM memories
                WHERE deleted_at IS NULL AND kind = ? AND content = ?
                LIMIT 1
                """,
                (kind, op.content.strip()),
            ).fetchone()
            if duplicate is not None:
                memory_id = duplicate["id"]
                merged_refs = list(
                    dict.fromkeys(json.loads(duplicate["source_refs"]) + source_refs)
                )
                db.execute(
                    """
                    UPDATE memories
                    SET source_refs = ?, confidence = ?, importance = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        json.dumps(merged_refs, ensure_ascii=False),
                        max(float(duplicate["confidence"]), confidence),
                        max(float(duplicate["importance"]), importance),
                        now,
                        memory_id,
                    ),
                )
                after = db.execute(
                    "SELECT * FROM memories WHERE id = ?",
                    (memory_id,),
                ).fetchone()
                self._log_event(
                    db, memory_id, "update", duplicate, after, run_id, now
                )
                return self._row_to_item(after)

            memory_id = str(uuid.uuid4())
            db.execute(
                """
                INSERT INTO memories(
                    id, kind, content, source_refs, confidence, importance,
                    metadata, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory_id,
                    kind,
                    op.content.strip(),
                    json.dumps(source_refs, ensure_ascii=False),
                    confidence,
                    importance,
                    json.dumps(metadata, ensure_ascii=False),
                    now,
                    now,
                ),
            )
        else:
            if before is None or before["deleted_at"] is not None:
                raise KeyError(f"memory not found: {op.id}")
            memory_id = op.id
            merged_refs = list(
                dict.fromkeys(json.loads(before["source_refs"]) + source_refs)
            )
            merged_meta = json.loads(before["metadata"])
            merged_meta.update(metadata)
            db.execute(
                """
                UPDATE memories
                SET kind = ?, content = ?, source_refs = ?, confidence = ?,
                    importance = ?, metadata = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    kind,
                    op.content.strip(),
                    json.dumps(merged_refs, ensure_ascii=False),
                    confidence,
                    importance,
                    json.dumps(merged_meta, ensure_ascii=False),
                    now,
                    memory_id,
                ),
            )

        after = db.execute(
            "SELECT * FROM memories WHERE id = ?",
            (memory_id,),
        ).fetchone()
        self._log_event(
            db, memory_id, op.action.value, before, after, run_id, now
        )
        return self._row_to_item(after)

    def _log_event(
        self,
        db: sqlite3.Connection,
        memory_id: str,
        action: str,
        before: sqlite3.Row | None,
        after: sqlite3.Row | None,
        run_id: str | None,
        now: str,
    ) -> None:
        db.execute(
            """
            INSERT INTO memory_events(
                memory_id, action, before_json, after_json, run_id, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                memory_id,
                action,
                json.dumps(dict(before), ensure_ascii=False) if before else None,
                json.dumps(dict(after), ensure_ascii=False) if after else None,
                run_id,
                now,
            ),
        )

    @staticmethod
    def _row_to_item(row: sqlite3.Row) -> MemoryItem:
        return MemoryItem(
            id=row["id"],
            kind=row["kind"],
            content=row["content"],
            source_refs=json.loads(row["source_refs"]),
            confidence=float(row["confidence"]),
            importance=float(row["importance"]),
            metadata=json.loads(row["metadata"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

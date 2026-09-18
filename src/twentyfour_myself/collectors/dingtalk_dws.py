from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Sequence

from ..models import Attachment, AuthorizationTier, Capability, Document, Message, Record
from .base import AuthorizationRequired, BaseCollector, CollectorContext, CollectorError


@dataclass(slots=True)
class DingTalkCollectRequest:
    group_conversation_ids: list[str] = field(default_factory=list)
    direct_user_ids: list[str] = field(default_factory=list)
    direct_open_dingtalk_ids: list[str] = field(default_factory=list)
    document_nodes: list[str] = field(default_factory=list)
    drive_nodes: list[str] = field(default_factory=list)
    time: str = "1970-01-01 00:00:00"
    forward: bool = True
    limit: int = 100
    all_start: str | None = None
    all_end: str | None = None


class DWSClient:
    """Adapter around DingTalk's officially open-sourced ``dws`` CLI.

    Credentials remain owned by dws. This project never reads browser cookies,
    local DingTalk databases, or DWS credential files directly.
    """

    def __init__(
        self,
        binary: str = "dws",
        *,
        profile: str | None = None,
        runner: Callable[[Sequence[str]], subprocess.CompletedProcess[str]] | None = None,
    ):
        self.binary = binary
        self.profile = profile
        self._custom_runner = runner is not None
        self._runner = runner or self._default_runner

    def _default_runner(self, args: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(args),
            capture_output=True,
            text=True,
            check=False,
            encoding="utf-8",
        )

    def available(self) -> bool:
        return True if self._custom_runner else shutil.which(self.binary) is not None

    def command(self, *parts: str) -> list[str]:
        cmd = [self.binary]
        if self.profile:
            cmd.extend(["--profile", self.profile])
        cmd.extend(parts)
        if "--format" not in cmd and "-f" not in cmd:
            cmd.extend(["--format", "json"])
        return cmd

    def run_json(self, *parts: str) -> dict[str, Any]:
        cmd = self.command(*parts)
        result = self._runner(cmd)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "dws command failed").strip()
            raise CollectorError(f"dws failed ({result.returncode}): {detail}")
        text = (result.stdout or "").strip()
        if not text:
            return {}
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise CollectorError(f"dws did not return JSON: {text[:300]}") from exc
        if isinstance(payload, dict) and payload.get("success") is False:
            raise CollectorError(f"dws returned an error: {payload}")
        return payload if isinstance(payload, dict) else {"result": payload}

    def auth_status(self) -> dict[str, Any]:
        return self.run_json("auth", "status")

    def ensure_authorized(self) -> None:
        if not self._custom_runner and shutil.which(self.binary) is None:
            raise AuthorizationRequired(
                "dws is not installed. Install DingTalk Workspace CLI and complete official authorization first."
            )
        status = self.auth_status()
        body = _unwrap_result(status)
        authenticated = _find_bool(body, "authenticated")
        token_valid = _find_bool(body, "token_valid", "tokenValid")
        if authenticated is False or token_valid is False:
            raise AuthorizationRequired(
                "DingTalk DWS is not authorized for the selected profile. Run the official `dws auth login` flow."
            )


class DingTalkDWSCollector(BaseCollector):
    source = "dingtalk_dws"

    def __init__(self, client: DWSClient, request: DingTalkCollectRequest):
        self.client = client
        self.request = request

    def capabilities(self) -> list[Capability]:
        return [
            Capability(
                "historical_group_messages",
                True,
                AuthorizationTier.ADMIN_APPROVED,
                "Uses dws chat message list --group; DWS organization access must be enabled/approved.",
            ),
            Capability(
                "historical_direct_messages",
                True,
                AuthorizationTier.ADMIN_APPROVED,
                "Uses dws chat message list --user/--open-dingtalk-id.",
            ),
            Capability(
                "cross_conversation_messages",
                True,
                AuthorizationTier.ADMIN_APPROVED,
                "Uses dws chat message list-all when a start/end window is supplied.",
            ),
            Capability(
                "message_search",
                False,
                AuthorizationTier.ADMIN_APPROVED,
                "DWS exposes message search upstream, but this collector does not expose it yet; history export is implemented instead.",
            ),
            Capability(
                "online_documents",
                True,
                AuthorizationTier.ADMIN_APPROVED,
                "Uses dws doc info + dws doc read for nodes explicitly supplied by the user.",
            ),
            Capability(
                "drive_files",
                True,
                AuthorizationTier.ADMIN_APPROVED,
                "Uses dws drive info + dws drive download for explicitly supplied nodes.",
            ),
            Capability(
                "chat_attachment_download",
                False,
                AuthorizationTier.ADMIN_APPROVED,
                "DWS message projections can be lossy; this version records resource identifiers when visible but does not claim generic chat-attachment download.",
            ),
            Capability(
                "without_admin_approval",
                False,
                AuthorizationTier.ADMIN_APPROVED,
                "DWS itself requires the organization to enable/approve CLI access.",
            ),
        ]

    def collect(self, context: CollectorContext) -> Iterable[Record]:
        self.client.ensure_authorized()
        for conversation_id in self.request.group_conversation_ids:
            yield from self._collect_conversation("--group", conversation_id)
        for user_id in self.request.direct_user_ids:
            yield from self._collect_conversation("--user", user_id)
        for open_id in self.request.direct_open_dingtalk_ids:
            yield from self._collect_conversation("--open-dingtalk-id", open_id)
        if self.request.all_start and self.request.all_end:
            yield from self._collect_all_messages(self.request.all_start, self.request.all_end)
        for node in self.request.document_nodes:
            yield self._collect_document(node)
        for node in self.request.drive_nodes:
            yield self._collect_drive_file(context, node)

    def _collect_conversation(self, selector: str, value: str) -> Iterator[Record]:
        cursor_time = self.request.time
        seen_pages: set[tuple[str, ...]] = set()
        while True:
            payload = self.client.run_json(
                "chat",
                "message",
                "list",
                selector,
                value,
                "--time",
                cursor_time,
                "--forward",
                "true" if self.request.forward else "false",
                "--limit",
                str(max(1, min(self.request.limit, 100))),
            )
            result = _unwrap_result(payload)
            messages = _extract_message_list(result)
            signature = tuple(str(m.get("openMessageId") or m.get("openMsgId") or "") for m in messages)
            if signature in seen_pages and signature:
                break
            if signature:
                seen_pages.add(signature)
            for item in messages:
                yield from self._records_from_message(item, fallback_channel=value)
            if not _find_bool(result, "hasMore", "has_more"):
                break
            if not messages:
                break
            next_time = str(messages[-1].get("createTime") or messages[-1].get("create_time") or "")
            if not next_time or next_time == cursor_time:
                break
            cursor_time = next_time

    def _collect_all_messages(self, start: str, end: str) -> Iterator[Record]:
        cursor = "0"
        seen_cursors: set[str] = set()
        while True:
            payload = self.client.run_json(
                "chat",
                "message",
                "list-all",
                "--start",
                start,
                "--end",
                end,
                "--limit",
                str(max(1, min(self.request.limit, 100))),
                "--cursor",
                cursor,
            )
            result = _unwrap_result(payload)
            for item in _extract_message_list(result):
                yield from self._records_from_message(item)
            if not _find_bool(result, "hasMore", "has_more"):
                break
            next_cursor = str(result.get("nextCursor") or result.get("next_cursor") or "")
            if not next_cursor or next_cursor in seen_cursors:
                break
            seen_cursors.add(next_cursor)
            cursor = next_cursor

    def _records_from_message(
        self, item: dict[str, Any], fallback_channel: str | None = None
    ) -> Iterator[Record]:
        message_id = str(item.get("openMessageId") or item.get("openMsgId") or item.get("messageId") or "")
        if not message_id:
            raw = json.dumps(item, ensure_ascii=False, sort_keys=True)
            import hashlib

            message_id = "synthetic-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
        channel = str(item.get("openConversationId") or fallback_channel or "") or None
        content = item.get("content")
        if isinstance(content, (dict, list)):
            text = _flatten_content(content)
        else:
            text = str(content or "")
        resources = list(_dingtalk_resource_ids(item))
        refs = [f"{message_id}:{kind}:{rid}" for kind, rid in resources]
        yield Message(
            source=self.source,
            external_id=message_id,
            channel_id=channel,
            sender_id=str(item.get("senderOpenDingTalkId") or item.get("senderId") or "") or None,
            sender_name=str(item.get("sender") or "") or None,
            timestamp=str(item.get("createTime") or item.get("create_time") or "") or None,
            text=text,
            attachment_refs=refs,
            metadata={
                "projection": "dws",
                "raw_type": item.get("msgType") or item.get("messageType"),
            },
        )
        for kind, resource_id in resources:
            yield Attachment(
                source=self.source,
                external_id=f"{message_id}:{kind}:{resource_id}",
                filename=resource_id,
                parent_ref=f"{self.source}:message:{message_id}",
                metadata={
                    "resource_id": resource_id,
                    "resource_kind": kind,
                    "downloaded": False,
                    "note": "Identifier surfaced by DWS message projection; generic chat-resource download is intentionally not assumed.",
                },
            )

    def _collect_document(self, node: str) -> Document:
        info = _unwrap_result(self.client.run_json("doc", "info", "--node", node))
        read = _unwrap_result(self.client.run_json("doc", "read", "--node", node))
        title = _first_string(info, "name", "title", "fileName") or node
        content = _first_string(read, "content", "markdown", "text", "body")
        if not content and isinstance(read, str):
            content = read
        return Document(
            source=self.source,
            external_id=_first_string(info, "nodeId", "node_id", "fileId") or node,
            title=title,
            content=content or "",
            owner_id=_first_string(info, "ownerId", "creatorId", "owner_id"),
            created_at=_first_string(info, "createTime", "createdAt", "created_at"),
            updated_at=_first_string(info, "updateTime", "updatedAt", "updated_at"),
            metadata={"node": node, "extension": info.get("extension"), "projection": "dws"},
        )

    def _collect_drive_file(self, context: CollectorContext, node: str) -> Attachment:
        info = _unwrap_result(self.client.run_json("drive", "info", "--node", node))
        filename = _safe_filename(
            _first_string(info, "name", "fileName", "title") or f"{_safe_filename(node)}.bin"
        )
        target = context.attachments_dir / f"dingtalk-{_safe_filename(node)}-{filename}"
        self.client.run_json(
            "drive",
            "download",
            "--node",
            node,
            "--output",
            str(target),
        )
        if not target.exists():
            raise CollectorError(
                f"dws drive download reported success but output file was not found: {target}"
            )
        return Attachment(
            source=self.source,
            external_id=f"drive:{_first_string(info, 'nodeId', 'dentryUuid', 'fileId') or node}",
            filename=filename,
            size=target.stat().st_size,
            local_path=str(target.relative_to(context.output_dir)),
            metadata={
                "node": node,
                "extension": info.get("extension"),
                "content_type": info.get("contentType"),
                "origin": "drive",
            },
        )


def _unwrap_result(payload: Any) -> Any:
    if isinstance(payload, dict) and "result" in payload:
        return payload["result"]
    return payload


def _extract_message_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("messages", "items", "list", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            nested = _extract_message_list(value)
            if nested:
                return nested
    return []


def _find_bool(payload: Any, *keys: str) -> bool | None:
    if not isinstance(payload, dict):
        return None
    for key in keys:
        if isinstance(payload.get(key), bool):
            return payload[key]
    for value in payload.values():
        result = _find_bool(value, *keys)
        if result is not None:
            return result
    return None


def _first_string(payload: Any, *keys: str) -> str | None:
    if isinstance(payload, str):
        return payload
    if not isinstance(payload, dict):
        return None
    for key in keys:
        value = payload.get(key)
        if isinstance(value, (str, int)) and str(value):
            return str(value)
    for value in payload.values():
        found = _first_string(value, *keys)
        if found:
            return found
    return None


def _flatten_content(value: Any) -> str:
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return value
        return _flatten_content(parsed)
    parts: list[str] = []

    def walk(node: Any, key: str | None = None) -> None:
        if isinstance(node, dict):
            for child_key, child in node.items():
                walk(child, child_key)
        elif isinstance(node, list):
            for child in node:
                walk(child, key)
        elif isinstance(node, (str, int, float)) and key in {
            "text",
            "content",
            "title",
            "name",
        }:
            val = str(node).strip()
            if val:
                parts.append(val)

    walk(value)
    return "\n".join(dict.fromkeys(parts))


def _dingtalk_resource_ids(item: Any) -> Iterator[tuple[str, str]]:
    found: set[tuple[str, str]] = set()

    def walk(node: Any) -> None:
        if isinstance(node, str):
            try:
                parsed = json.loads(node)
            except json.JSONDecodeError:
                return
            walk(parsed)
        elif isinstance(node, dict):
            for key, value in node.items():
                normalized = key.lower()
                if normalized in {"fileid", "resourceid", "mediaid"} and isinstance(value, str) and value:
                    found.add((normalized, value))
                walk(value)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(item)
    yield from sorted(found)


def _safe_filename(name: str) -> str:
    value = Path(str(name)).name
    return re.sub(r"[^\w.()\[\] =+-]+", "_", value, flags=re.UNICODE).strip() or "file"

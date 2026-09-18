from __future__ import annotations

import json
import mimetypes
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator
from urllib.parse import quote

import httpx

from ..models import Attachment, AuthorizationTier, Capability, Document, Message, Record
from .base import AuthorizationRequired, BaseCollector, CollectorContext, CollectorError


@dataclass(slots=True)
class FeishuCollectRequest:
    chat_ids: list[str] = field(default_factory=list)
    document_ids: list[str] = field(default_factory=list)
    drive_files: list[tuple[str, str | None]] = field(default_factory=list)
    start_time: int | None = None
    end_time: int | None = None
    page_size: int = 50
    download_message_attachments: bool = False


class FeishuHTTPClient:
    """Minimal official Feishu OpenAPI client.

    A user access token obtained through an official OAuth flow can be supplied
    directly. For an internal enterprise app, ``from_internal_app`` obtains an
    official tenant_access_token from Feishu.
    """

    def __init__(
        self,
        access_token: str,
        *,
        base_url: str = "https://open.feishu.cn/open-apis",
        client: httpx.Client | None = None,
    ):
        if not access_token:
            raise AuthorizationRequired("Feishu access token is required")
        self.access_token = access_token
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=30.0, follow_redirects=True)
        self._owns_client = client is None

    @classmethod
    def from_internal_app(
        cls,
        app_id: str,
        app_secret: str,
        *,
        base_url: str = "https://open.feishu.cn/open-apis",
        client: httpx.Client | None = None,
    ) -> "FeishuHTTPClient":
        http = client or httpx.Client(timeout=30.0, follow_redirects=True)
        response = http.post(
            f"{base_url.rstrip('/')}/auth/v3/tenant_access_token/internal",
            json={"app_id": app_id, "app_secret": app_secret},
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("code", 0) != 0:
            raise AuthorizationRequired(
                f"Feishu tenant token request failed: {payload.get('msg', 'unknown error')}"
            )
        token = payload.get("tenant_access_token")
        if not token:
            raise AuthorizationRequired("Feishu did not return a tenant_access_token")
        instance = cls(token, base_url=base_url, client=http)
        instance._owns_client = client is None
        return instance

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}

    def get_json(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self._client.get(
            f"{self.base_url}/{path.lstrip('/')}",
            headers=self._headers(),
            params=params,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("code", 0) != 0:
            raise CollectorError(
                f"Feishu API error {payload.get('code')}: {payload.get('msg', 'unknown error')}"
            )
        return payload.get("data") or {}

    def get_bytes(
        self, path: str, *, params: dict[str, Any] | None = None
    ) -> tuple[bytes, httpx.Headers]:
        response = self._client.get(
            f"{self.base_url}/{path.lstrip('/')}",
            headers=self._headers(),
            params=params,
        )
        response.raise_for_status()
        return response.content, response.headers


class FeishuCollector(BaseCollector):
    source = "feishu"

    def __init__(self, client: FeishuHTTPClient, request: FeishuCollectRequest):
        self.client = client
        self.request = request

    def capabilities(self) -> list[Capability]:
        return [
            Capability(
                "historical_messages",
                True,
                AuthorizationTier.ADMIN_APPROVED,
                "Uses GET /im/v1/messages. App permissions/data scope still apply.",
            ),
            Capability(
                "message_resources",
                True,
                AuthorizationTier.ADMIN_APPROVED,
                "Uses the official message resource endpoint; Feishu imposes resource and bot/chat constraints.",
            ),
            Capability(
                "docx_raw_content",
                True,
                AuthorizationTier.USER_DELEGATED,
                "Official docx raw_content accepts authorized access tokens subject to document permissions.",
            ),
            Capability(
                "drive_file_download",
                True,
                AuthorizationTier.USER_DELEGATED,
                "Downloads ordinary Drive files; online docs require document/export APIs instead.",
            ),
            Capability(
                "bulk_all_user_data",
                False,
                AuthorizationTier.ADMIN_APPROVED,
                "No bypass or implicit account-wide export is implemented.",
            ),
        ]

    def collect(self, context: CollectorContext) -> Iterable[Record]:
        for chat_id in self.request.chat_ids:
            yield from self._collect_chat(context, chat_id)
        for document_id in self.request.document_ids:
            yield self._collect_document(document_id)
        for token, filename in self.request.drive_files:
            yield self._collect_drive_file(context, token, filename)

    def _collect_chat(self, context: CollectorContext, chat_id: str) -> Iterator[Record]:
        page_token: str | None = None
        while True:
            params: dict[str, Any] = {
                "container_id_type": "chat",
                "container_id": chat_id,
                "page_size": max(1, min(self.request.page_size, 50)),
            }
            if self.request.start_time is not None:
                params["start_time"] = self.request.start_time
            if self.request.end_time is not None:
                params["end_time"] = self.request.end_time
            if page_token:
                params["page_token"] = page_token
            data = self.client.get_json("im/v1/messages", params=params)
            for item in data.get("items") or []:
                message, resources = self._message_from_item(chat_id, item)
                for resource in resources:
                    if self.request.download_message_attachments:
                        self._download_message_resource(context, message, resource)
                    yield resource
                yield message
            if not data.get("has_more"):
                break
            new_token = data.get("page_token")
            if not new_token or new_token == page_token:
                break
            page_token = new_token

    def _message_from_item(
        self, chat_id: str, item: dict[str, Any]
    ) -> tuple[Message, list[Attachment]]:
        message_id = str(item.get("message_id") or item.get("messageId") or "")
        if not message_id:
            raise CollectorError("Feishu message response missing message_id")
        body = item.get("body") or {}
        raw_content = body.get("content") or ""
        parsed = _json_or_text(raw_content)
        text = _extract_readable_text(parsed)
        sender = item.get("sender") or {}
        resources: list[Attachment] = []
        refs: list[str] = []
        for resource_type, key, filename in _extract_resources(parsed):
            attachment_id = f"{message_id}:{key}"
            refs.append(attachment_id)
            resources.append(
                Attachment(
                    source=self.source,
                    external_id=attachment_id,
                    filename=filename or key,
                    parent_ref=f"{self.source}:message:{message_id}",
                    metadata={
                        "message_id": message_id,
                        "resource_key": key,
                        "resource_type": resource_type,
                    },
                )
            )
        message = Message(
            source=self.source,
            external_id=message_id,
            channel_id=chat_id,
            sender_id=str(sender.get("id") or "") or None,
            sender_name=None,
            timestamp=_milliseconds_to_iso(item.get("create_time")),
            text=text,
            attachment_refs=refs,
            metadata={
                "msg_type": item.get("msg_type"),
                "root_id": item.get("root_id"),
                "parent_id": item.get("parent_id"),
                "deleted": item.get("deleted", False),
                "updated_at": _milliseconds_to_iso(item.get("update_time")),
                "sender_id_type": sender.get("id_type"),
                "sender_type": sender.get("sender_type"),
            },
        )
        return message, resources

    def _download_message_resource(
        self, context: CollectorContext, message: Message, attachment: Attachment
    ) -> None:
        resource_type = attachment.metadata["resource_type"]
        key = attachment.metadata["resource_key"]
        payload, headers = self.client.get_bytes(
            f"im/v1/messages/{quote(message.external_id, safe='')}/resources/{quote(key, safe='')}",
            params={"type": resource_type},
        )
        filename = _filename_from_headers(headers) or attachment.filename or key
        filename = _safe_filename(filename)
        target = context.attachments_dir / f"feishu-{_safe_filename(message.external_id)}-{filename}"
        target.write_bytes(payload)
        attachment.filename = filename
        attachment.mime_type = headers.get("content-type") or mimetypes.guess_type(filename)[0]
        attachment.size = len(payload)
        attachment.local_path = str(target.relative_to(context.output_dir))

    def _collect_document(self, document_id: str) -> Document:
        meta = self.client.get_json(f"docx/v1/documents/{quote(document_id, safe='')}")
        raw = self.client.get_json(
            f"docx/v1/documents/{quote(document_id, safe='')}/raw_content"
        )
        doc = meta.get("document") or {}
        return Document(
            source=self.source,
            external_id=document_id,
            title=str(doc.get("title") or ""),
            content=str(raw.get("content") or ""),
            metadata={"revision_id": doc.get("revision_id"), "type": "docx"},
        )

    def _collect_drive_file(
        self, context: CollectorContext, file_token: str, filename: str | None
    ) -> Attachment:
        payload, headers = self.client.get_bytes(
            f"drive/v1/files/{quote(file_token, safe='')}/download"
        )
        resolved = filename or _filename_from_headers(headers) or file_token
        resolved = _safe_filename(resolved)
        target = context.attachments_dir / f"feishu-drive-{_safe_filename(file_token)}-{resolved}"
        target.write_bytes(payload)
        return Attachment(
            source=self.source,
            external_id=f"drive:{file_token}",
            filename=resolved,
            mime_type=headers.get("content-type") or mimetypes.guess_type(resolved)[0],
            size=len(payload),
            local_path=str(target.relative_to(context.output_dir)),
            metadata={"file_token": file_token, "origin": "drive"},
        )


def _json_or_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _extract_readable_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    parts: list[str] = []

    def walk(node: Any, key: str | None = None) -> None:
        if isinstance(node, dict):
            for child_key, child in node.items():
                if child_key in {"file_key", "image_key", "file_name"}:
                    continue
                walk(child, child_key)
        elif isinstance(node, list):
            for child in node:
                walk(child, key)
        elif isinstance(node, (str, int, float)) and key in {
            "text",
            "title",
            "content",
            "name",
        }:
            text = str(node).strip()
            if text:
                parts.append(text)

    walk(value)
    return "\n".join(dict.fromkeys(parts)).strip()


def _extract_resources(value: Any) -> list[tuple[str, str, str | None]]:
    found: list[tuple[str, str, str | None]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            filename = node.get("file_name") or node.get("name")
            if isinstance(node.get("file_key"), str):
                found.append(("file", node["file_key"], filename if isinstance(filename, str) else None))
            if isinstance(node.get("image_key"), str):
                found.append(("image", node["image_key"], filename if isinstance(filename, str) else None))
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(value)
    unique: dict[tuple[str, str], tuple[str, str, str | None]] = {}
    for item in found:
        unique[(item[0], item[1])] = item
    return list(unique.values())


def _milliseconds_to_iso(value: Any) -> str | None:
    if value in (None, ""):
        return None
    try:
        from datetime import datetime, timezone

        number = int(value)
        seconds = number / 1000 if number > 10_000_000_000 else number
        return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat()
    except (ValueError, TypeError, OverflowError, OSError):
        return str(value)


def _filename_from_headers(headers: httpx.Headers) -> str | None:
    disposition = headers.get("content-disposition", "")
    match = re.search(r"filename\*=UTF-8''([^;]+)", disposition, flags=re.I)
    if match:
        from urllib.parse import unquote

        return unquote(match.group(1)).strip('"')
    match = re.search(r'filename="?([^";]+)"?', disposition, flags=re.I)
    return match.group(1).strip() if match else None


def _safe_filename(name: str) -> str:
    name = Path(name).name
    return re.sub(r"[^\w.()\[\] -]+", "_", name, flags=re.UNICODE).strip() or "file.bin"

from __future__ import annotations

import hashlib
import mailbox
import mimetypes
import re
from email import policy
from email.header import decode_header, make_header
from email.message import Message as EmailMessage
from email.parser import BytesParser
from email.utils import parseaddr, parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable

from ..models import Attachment, AuthorizationTier, Capability, Message, Record
from .base import BaseCollector, CollectorContext, CollectorError


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data)

    def text(self) -> str:
        return "\n".join(part.strip() for part in self.parts if part.strip())


def _decode_header(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def _safe_filename(name: str) -> str:
    name = Path(name).name
    name = re.sub(r"[^\w.()\[\] -]+", "_", name, flags=re.UNICODE).strip()
    return name or "attachment.bin"


def _payload_bytes(part: EmailMessage) -> bytes:
    payload = part.get_payload(decode=True)
    if payload is not None:
        return payload
    raw = part.get_payload()
    if isinstance(raw, str):
        charset = part.get_content_charset() or "utf-8"
        return raw.encode(charset, errors="replace")
    return b""


def _decode_text_part(part: EmailMessage) -> str:
    data = _payload_bytes(part)
    charset = part.get_content_charset() or "utf-8"
    try:
        return data.decode(charset, errors="replace")
    except LookupError:
        return data.decode("utf-8", errors="replace")


def _message_body(msg: EmailMessage) -> str:
    plain: list[str] = []
    html: list[str] = []
    parts = msg.walk() if msg.is_multipart() else [msg]
    for part in parts:
        if part.is_multipart():
            continue
        disposition = (part.get_content_disposition() or "").lower()
        if disposition == "attachment" or part.get_filename():
            continue
        content_type = part.get_content_type()
        if content_type == "text/plain":
            plain.append(_decode_text_part(part))
        elif content_type == "text/html":
            html.append(_decode_text_part(part))
    if plain:
        return "\n\n".join(item.strip() for item in plain if item.strip()).strip()
    if html:
        parser = _HTMLTextExtractor()
        parser.feed("\n".join(html))
        return parser.text().strip()
    return ""


class MboxCollector(BaseCollector):
    source = "email_mbox"

    def __init__(self, path: str | Path, *, save_attachments: bool = True):
        self.path = Path(path)
        self.save_attachments = save_attachments

    def capabilities(self) -> list[Capability]:
        return [
            Capability(
                "messages",
                True,
                AuthorizationTier.USER_FILE,
                "Reads only a user-provided mbox export.",
            ),
            Capability(
                "attachments",
                True,
                AuthorizationTier.USER_FILE,
                "Attachments are extracted locally from the provided mbox.",
            ),
            Capability(
                "remote_mailbox",
                False,
                AuthorizationTier.USER_DELEGATED,
                "No Gmail/Outlook account login is performed by the mbox collector.",
            ),
        ]

    def collect(self, context: CollectorContext) -> Iterable[Record]:
        if not self.path.exists():
            raise CollectorError(f"mbox file does not exist: {self.path}")

        parser = BytesParser(policy=policy.default)
        mbox = mailbox.mbox(self.path, factory=lambda f: parser.parse(f))
        try:
            for raw_msg in mbox:
                msg: EmailMessage = raw_msg
                raw_bytes = msg.as_bytes(policy=policy.default)
                fallback_id = hashlib.sha256(raw_bytes).hexdigest()
                message_id = (msg.get("Message-ID") or "").strip().strip("<>") or fallback_id
                subject = _decode_header(msg.get("Subject"))
                sender_name, sender_email = parseaddr(_decode_header(msg.get("From")))
                timestamp = None
                if msg.get("Date"):
                    try:
                        timestamp = parsedate_to_datetime(msg.get("Date")).isoformat()
                    except (TypeError, ValueError, OverflowError):
                        timestamp = None

                attachment_refs: list[str] = []
                attachments: list[Attachment] = []
                for index, part in enumerate(msg.walk() if msg.is_multipart() else []):
                    filename = part.get_filename()
                    disposition = (part.get_content_disposition() or "").lower()
                    if not filename and disposition != "attachment":
                        continue
                    payload = _payload_bytes(part)
                    if not payload:
                        continue
                    decoded_name = _decode_header(filename) if filename else f"attachment-{index}.bin"
                    safe_name = _safe_filename(decoded_name)
                    digest = hashlib.sha256(payload).hexdigest()
                    attachment_id = f"{message_id}:{index}:{digest[:16]}"
                    attachment_refs.append(attachment_id)
                    local_path: str | None = None
                    if self.save_attachments:
                        target = context.attachments_dir / f"{digest[:16]}-{safe_name}"
                        if not target.exists():
                            target.write_bytes(payload)
                        local_path = str(target.relative_to(context.output_dir))
                    attachments.append(
                        Attachment(
                            source=self.source,
                            external_id=attachment_id,
                            filename=safe_name,
                            mime_type=part.get_content_type()
                            or mimetypes.guess_type(safe_name)[0],
                            size=len(payload),
                            local_path=local_path,
                            parent_ref=f"{self.source}:message:{message_id}",
                            metadata={"content_disposition": disposition or None},
                        )
                    )

                yield Message(
                    source=self.source,
                    external_id=message_id,
                    channel_id="mailbox",
                    sender_id=sender_email or None,
                    sender_name=sender_name or sender_email or None,
                    timestamp=timestamp,
                    text=_message_body(msg),
                    attachment_refs=attachment_refs,
                    metadata={
                        "subject": subject,
                        "from": _decode_header(msg.get("From")),
                        "to": _decode_header(msg.get("To")),
                        "cc": _decode_header(msg.get("Cc")),
                        "in_reply_to": (msg.get("In-Reply-To") or "").strip() or None,
                        "references": (msg.get("References") or "").strip() or None,
                        "source_file": self.path.name,
                    },
                )
                yield from attachments
        finally:
            mbox.close()

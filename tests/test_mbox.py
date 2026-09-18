import mailbox
from email.message import EmailMessage

from twentyfour_myself.collectors.base import CollectorContext
from twentyfour_myself.collectors.mbox import MboxCollector
from twentyfour_myself.models import Attachment, Message


def test_mbox_parses_body_and_attachment(tmp_path):
    path = tmp_path / "mail.mbox"
    box = mailbox.mbox(path, create=True)
    msg = EmailMessage()
    msg["Message-ID"] = "<abc@example.com>"
    msg["From"] = "Alice <alice@example.com>"
    msg["To"] = "Bob <bob@example.com>"
    msg["Subject"] = "Hello"
    msg.set_content("plain body")
    msg.add_attachment(b"hello file", maintype="application", subtype="octet-stream", filename="a.txt")
    box.add(msg)
    box.flush()
    box.close()

    output = tmp_path / "corpus"
    records = list(MboxCollector(path).collect(CollectorContext(output)))
    messages = [r for r in records if isinstance(r, Message)]
    attachments = [r for r in records if isinstance(r, Attachment)]
    assert len(messages) == 1
    assert messages[0].text == "plain body"
    assert messages[0].sender_id == "alice@example.com"
    assert len(attachments) == 1
    assert (output / attachments[0].local_path).read_bytes() == b"hello file"

import json

import httpx

from twentyfour_myself.collectors.base import CollectorContext
from twentyfour_myself.collectors.feishu import FeishuCollectRequest, FeishuCollector, FeishuHTTPClient
from twentyfour_myself.models import Attachment, Document, Message


def test_feishu_normalizes_messages_docs_and_resource(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/im/v1/messages"):
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "msg": "success",
                    "data": {
                        "has_more": False,
                        "items": [
                            {
                                "message_id": "om1",
                                "msg_type": "post",
                                "create_time": "1700000000000",
                                "sender": {"id": "ou1", "id_type": "open_id", "sender_type": "user"},
                                "body": {
                                    "content": json.dumps(
                                        {
                                            "title": "Title",
                                            "content": [[{"tag": "text", "text": "hello"}, {"tag": "img", "image_key": "img1"}]],
                                        }
                                    )
                                },
                            }
                        ],
                    },
                },
            )
        if path.endswith("/im/v1/messages/om1/resources/img1"):
            return httpx.Response(
                200,
                content=b"image-bytes",
                headers={"content-type": "image/png", "content-disposition": 'attachment; filename="x.png"'},
            )
        if path.endswith("/docx/v1/documents/doc1/raw_content"):
            return httpx.Response(200, json={"code": 0, "data": {"content": "doc body"}})
        if path.endswith("/docx/v1/documents/doc1"):
            return httpx.Response(200, json={"code": 0, "data": {"document": {"title": "Doc", "revision_id": 3}}})
        raise AssertionError(f"unexpected request: {request.url}")

    http = httpx.Client(transport=httpx.MockTransport(handler))
    client = FeishuHTTPClient("token", client=http)
    request = FeishuCollectRequest(
        chat_ids=["oc1"],
        document_ids=["doc1"],
        download_message_attachments=True,
    )
    records = list(FeishuCollector(client, request).collect(CollectorContext(tmp_path)))
    message = next(r for r in records if isinstance(r, Message))
    attachment = next(r for r in records if isinstance(r, Attachment))
    document = next(r for r in records if isinstance(r, Document))
    assert "hello" in message.text
    assert attachment.filename == "x.png"
    assert (tmp_path / attachment.local_path).read_bytes() == b"image-bytes"
    assert document.content == "doc body"

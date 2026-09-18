import json
import subprocess

from twentyfour_myself.collectors.base import CollectorContext
from twentyfour_myself.collectors.dingtalk_dws import DWSClient, DingTalkCollectRequest, DingTalkDWSCollector
from twentyfour_myself.models import Message


def test_dws_group_history_normalization(tmp_path):
    calls = []

    def runner(args):
        calls.append(list(args))
        if "auth" in args and "status" in args:
            payload = {"result": {"authenticated": True, "token_valid": True}, "success": True}
        elif "list" in args:
            payload = {
                "result": {
                    "hasMore": False,
                    "messages": [
                        {
                            "openMessageId": "m1",
                            "openConversationId": "cid1",
                            "content": "hello",
                            "createTime": "2026-09-01 10:00:00",
                            "sender": "Alice",
                            "senderOpenDingTalkId": "D1",
                        }
                    ],
                },
                "success": True,
            }
        else:
            raise AssertionError(args)
        return subprocess.CompletedProcess(args, 0, stdout=json.dumps(payload), stderr="")

    collector = DingTalkDWSCollector(
        DWSClient(runner=runner),
        DingTalkCollectRequest(group_conversation_ids=["cid1"], time="2026-09-01 00:00:00"),
    )
    records = list(collector.collect(CollectorContext(tmp_path)))
    message = next(r for r in records if isinstance(r, Message))
    assert message.external_id == "m1"
    assert message.channel_id == "cid1"
    assert message.sender_name == "Alice"
    assert any("--group" in call for call in calls)

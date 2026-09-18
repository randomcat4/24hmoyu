from twentyfour_myself.models import Message, record_from_dict


def test_message_roundtrip():
    message = Message(source="x", external_id="1", channel_id="c", text="hello")
    restored = record_from_dict(message.to_dict())
    assert isinstance(restored, Message)
    assert restored.stable_key == "x:message:1"
    assert restored.text == "hello"

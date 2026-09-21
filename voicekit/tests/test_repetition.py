from voicekit.repetition import audit_documents


def test_repetition_audit_detects_shared_opening():
    texts = [
        "Same opening words appear here and then the rest changes significantly for document one.",
        "Same opening words appear here and then another path follows for document two.",
    ]
    result = audit_documents(texts)
    assert result["documents"] == 2
    assert result["duplicate_opening_heads"]

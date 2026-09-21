from voicekit.lineup import Document, build_lineup, select_matched_controls


def _text(n: int) -> str:
    return "word " * n


def test_matching_prefers_same_mode_register_and_length():
    fake = Document("fake", _text(100), mode="analysis", register="casual", era="recent")
    candidates = [
        Document("good1", _text(95), mode="analysis", register="casual", era="recent"),
        Document("good2", _text(105), mode="analysis", register="casual", era="recent"),
        Document("bad-mode", _text(100), mode="narrative", register="casual", era="recent"),
        Document("bad-register", _text(100), mode="analysis", register="formal", era="recent"),
        Document("good3", _text(120), mode="analysis", register="casual", era="recent"),
        Document("good4", _text(80), mode="analysis", register="casual", era="recent"),
        Document("good5", _text(130), mode="analysis", register="casual", era="recent"),
        Document("good6", _text(70), mode="analysis", register="casual", era="recent"),
        Document("good7", _text(140), mode="analysis", register="casual", era="recent"),
        Document("other", _text(100), mode="narrative", register="formal", era="old"),
    ]
    selected = select_matched_controls(fake, candidates, n=7)
    assert "bad-mode" not in {d.id for d in selected}
    assert "bad-register" not in {d.id for d in selected}


def test_build_lineup_has_one_fake_and_seven_controls():
    fake = Document("fake", _text(100))
    reals = [Document(f"r{i}", _text(90 + i)) for i in range(10)]
    lineup, key = build_lineup(fake, reals, seed=3)
    assert len(key["labels"]) == 8
    assert len(key["control_ids"]) == 7
    assert key["labels"][key["fake_label"]] == "fake"
    assert lineup.count("## TEXT ") == 8

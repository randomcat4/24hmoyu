from voicekit.measure import measure_text, profile_documents


def test_measure_text_captures_core_signals():
    text = """
    I think this probably works, but I would test it first.

    However, you should not assume the easy case. Here's why: the second path is longer, and it matters.

    We tried it twice. It worked once! The other run failed.
    """
    metrics = measure_text(text)
    assert metrics["totals"]["words"] > 20
    assert abs(sum(metrics["sentence"]["length_words"]["histogram_p"]) - 1.0) < 1e-9
    assert metrics["stance"]["first_person_rate"] > 0
    assert metrics["stance"]["second_person_rate"] > 0
    assert metrics["punctuation"]["rates_per_1000w"]["colons"] > 0


def test_profile_documents_retains_document_level_metrics():
    profile = profile_documents([
        ("a", "I write short things. Then I stop."),
        ("b", "Sometimes I write a much longer sentence because the explanation actually needs room to breathe before it lands."),
    ])
    assert profile["schema_version"] == 1
    assert [row["id"] for row in profile["documents"]] == ["a", "b"]
    assert profile["aggregate"]["totals"]["words"] >= sum(
        row["metrics"]["totals"]["words"] for row in profile["documents"]
    )

from voicekit.distance import candidate_typicality, style_distance
from voicekit.measure import measure_text


def test_identical_text_has_zero_distance():
    metrics = measure_text("I think this works. But maybe test it twice. Then ship it.")
    result = style_distance(metrics, metrics)
    assert result["distance"] == 0.0


def test_candidate_typicality_uses_real_real_baseline():
    docs = [
        measure_text("I think this works. But test it. Then ship."),
        measure_text("I think it works, though I would test the edge case before shipping it."),
        measure_text("Maybe it works. I would test it first, then ship."),
    ]
    candidate = measure_text("I think this probably works. Test it first, then ship it.")
    result = candidate_typicality(candidate, docs)
    assert 0 <= result["distance_percentile"] <= 100
    assert result["candidate_median_distance"] >= 0
    assert "p95" in result["baseline"]

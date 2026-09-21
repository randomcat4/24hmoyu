from __future__ import annotations

import math
import statistics
from typing import Any, Sequence

DEFAULT_WEIGHTS = {
    "function_words": 0.20,
    "sentence": 0.16,
    "paragraph": 0.10,
    "punctuation": 0.12,
    "stance": 0.10,
    "rhetoric": 0.08,
    "syntax": 0.08,
    "paragraph_cadence": 0.07,
    "repetition": 0.05,
    "orthography": 0.04,
}


def _normalize(values: Sequence[float]) -> list[float]:
    vals = [max(0.0, float(v)) for v in values]
    total = sum(vals)
    if total <= 0:
        return [1.0 / len(vals) for _ in vals] if vals else []
    return [v / total for v in vals]


def _js_distance(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 1.0
    p = _normalize(a)
    q = _normalize(b)
    m = [(x + y) / 2.0 for x, y in zip(p, q)]
    eps = 1e-12

    def kl(x: Sequence[float], y: Sequence[float]) -> float:
        out = 0.0
        for xi, yi in zip(x, y):
            if xi > 0:
                out += xi * math.log((xi + eps) / (yi + eps), 2)
        return out

    js = 0.5 * kl(p, m) + 0.5 * kl(q, m)
    return max(0.0, min(1.0, js))


def _relative_distance(a: float, b: float) -> float:
    denom = max((abs(a) + abs(b)) / 2.0, 1e-9)
    return max(0.0, min(1.0, abs(a - b) / denom))


def _dict_distance(a: dict[str, Any], b: dict[str, Any]) -> float:
    keys = sorted(
        k for k in set(a) | set(b)
        if isinstance(a.get(k, 0.0), (int, float)) and isinstance(b.get(k, 0.0), (int, float))
    )
    if not keys:
        return 0.0
    return statistics.mean(_relative_distance(float(a.get(k, 0.0)), float(b.get(k, 0.0))) for k in keys)


def _distribution_dict_distance(a: dict[str, Any], b: dict[str, Any]) -> float:
    keys = sorted(set(a) | set(b))
    if not keys:
        return 0.0
    av = [float(a.get(k, 0.0)) for k in keys]
    bv = [float(b.get(k, 0.0)) for k in keys]
    return _js_distance(av, bv)


def style_distance(
    a: dict,
    b: dict,
    *,
    weights: dict[str, float] | None = None,
) -> dict:
    """Return an interpretable 0..1 style distance between two metric bundles.

    The output is intentionally a distance, not a calibrated probability. Lower
    means more similar. Component weights are defaults for inspection and should
    be changed only after empirical calibration for a particular corpus.
    """
    w = dict(DEFAULT_WEIGHTS)
    if weights:
        for key, value in weights.items():
            if key in w and isinstance(value, (int, float)) and value >= 0:
                w[key] = float(value)

    components: dict[str, float] = {}
    components["sentence"] = _js_distance(
        a.get("sentence", {}).get("length_words", {}).get("histogram_p", []),
        b.get("sentence", {}).get("length_words", {}).get("histogram_p", []),
    )
    components["paragraph"] = statistics.mean([
        _js_distance(
            a.get("paragraph", {}).get("length_sentences_histogram_p", []),
            b.get("paragraph", {}).get("length_sentences_histogram_p", []),
        ),
        _relative_distance(
            float(a.get("paragraph", {}).get("one_sentence_paragraph_rate", 0.0)),
            float(b.get("paragraph", {}).get("one_sentence_paragraph_rate", 0.0)),
        ),
    ])
    components["function_words"] = _distribution_dict_distance(
        a.get("function_words", {}).get("rates_per_1000w", {}),
        b.get("function_words", {}).get("rates_per_1000w", {}),
    )
    components["punctuation"] = _dict_distance(
        a.get("punctuation", {}).get("rates_per_1000w", {}),
        b.get("punctuation", {}).get("rates_per_1000w", {}),
    )
    components["stance"] = _dict_distance(a.get("stance", {}), b.get("stance", {}))
    components["rhetoric"] = _dict_distance(a.get("rhetoric", {}), b.get("rhetoric", {}))
    components["syntax"] = _dict_distance(a.get("syntax", {}), b.get("syntax", {}))
    components["paragraph_cadence"] = _dict_distance(
        a.get("paragrap_cadence", {}), b.get("paragraph_cadence", {})
    )
    components["repetition"] = _dict_distance(a.get("repetition", {}), b.get("repetition", {}))
    components["orthography"] = _dict_distance(a.get("orthography", {}), b.get("orthography", {}))

    used = [(name, w[name], dist) for name, dist in components.items() if w.get(name, 0.0) > 0]
    total_weight = sum(weight for _, weight, _ in used)
    distance = (
        sum(weight * dist for _, weight, dist in used) / total_weight
        if total_weight else 0.0
    )
    ordered = sorted(
        ({"name": name, "distance": round(dist, 6), "weight": weight} for name, weight, dist in used),
        key=lambda row: row["distance"],
        reverse=True,
    )
    return {
        "distance": round(distance, 6),
        "components": ordered,
        "note": "This is an interpretable heuristic distance, not a calibrated authorship probability.",
    }


def _quantile(values: Sequence[float], q: float) -> float:
    vals = sorted(float(v) for v in values)
    if not vals:
        return 0.0
    if len(vals) == 1:
        return vals[0]
    pos = (len(vals) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return vals[lo]
    frac = pos - lo
    return vals[lo] * (1 - frac) + vals[hi] * frac


def real_real_baseline(document_metrics: Sequence[dict]) -> dict:
    """Build a within-author baseline from each real document's median distance to peers."""
    docs = list(document_metrics)
    if len(docs) < 2:
        raise ValueError("need at least two real documents")
    per_document: list[float] = []
    pairwise: list[float] = []
    for i, doc in enumerate(docs):
        dists = []
        for j, other in enumerate(docs):
            if i == j:
                continue
            d = style_distance(doc, other)["distance"]
            dists.append(d)
            if i < j:
                pairwise.append(d)
        per_document.append(statistics.median(dists))
    return {
        "real_document_median_distances": per_document,
        "pairwise_distances": pairwise,
        "p50": round(_quantile(per_document, 0.50), 6),
        "p90": round(_quantile(per_document, 0.90), 6),
        "p95": round(_quantile(per_document, 0.95), 6),
    }


def candidate_typicality(candidate: dict, document_metrics: Sequence[dict]) -> dict:
    """Place a candidate inside the author's real-real distance distribution.

    Percentile is 'distance percentile': higher means more atypical. It is not a
    probability of authorship.
    """
    docs = list(document_metrics)
    baseline = real_real_baseline(docs)
    candidate_distances = [style_distance(candidate, doc)["distance"] for doc in docs]
    candidate_median = statistics.median(candidate_distances)
    real_medians = baseline["real_document_median_distances"]
    percentile = 100.0 * sum(v <= candidate_median for v in real_medians) / len(real_medians)
    return {
        "candidate_median_distance": round(candidate_median, 6),
        "distance_percentile": round(percentile, 2),
        "baseline": {k: baseline[k] for k in ("p50", "p90", "p95")},
        "interpretation": "Higher percentile means the candidate is farther from real texts than more of the author's own texts.",
    }

from __future__ import annotations

import math
import re
import statistics
from collections import Counter
from pathlib import Path
from typing import Iterable, Sequence

WORD_RE = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)?|\d+(?:[.,]\d+)*")
FENCE_RE = re.compile(r"```.*?```|~~~.*?~~~", re.S)
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
HTML_TAG_RE = re.compile(r"<[^>\n]{1,200}>")
LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
HEADING_RE = re.compile(r"(?m)^\s{0,3}#{1,6}\s+")
LIST_RE = re.compile(r"(?m)^\s*(?:[-*+]\s+|\d+[.)]\s+)")
BLOCKQUOTE_RE = re.compile(r"(?m)^\s*>\s?")

FUNCTION_WORDS = [
    "the", "a", "an", "and", "or", "but", "if", "then", "because", "so",
    "while", "although", "though", "of", "in", "on", "for", "with", "as",
    "by", "from", "to", "into", "over", "under", "between", "is", "are",
    "was", "were", "be", "been", "being", "it", "this", "that", "these",
    "those", "i", "we", "you", "he", "she", "they", "me", "us", "him",
    "her", "them", "my", "our", "your", "their", "not", "no", "nor",
    "very", "also", "even", "only", "just", "rather", "however", "therefore",
]
HEDGES = {
    "may", "might", "perhaps", "possibly", "probably", "likely", "roughly",
    "generally", "usually", "often", "sometimes", "seems", "appears", "suggests",
}
BOOSTERS = {"clearly", "obviously", "certainly", "definitely", "indeed", "surely", "must"}
DIRECTIVES = {"must", "should", "need", "needs", "ought", "required"}
FIRST_PERSON = {"i", "me", "my", "mine", "we", "us", "our", "ours"}
SECOND_PERSON = {"you", "your", "yours"}
THIRD_PERSON = {"he", "him", "his", "she", "her", "hers", "they", "them", "their", "theirs"}
SUBORDINATORS = {
    "because", "although", "though", "while", "if", "when", "since", "unless",
    "whereas", "after", "before", "once", "until",
}
TRANSITIONS = [
    "however", "therefore", "moreover", "furthermore", "nevertheless", "nonetheless",
    "for example", "for instance", "in short", "in sum", "in practice", "in effect",
    "first", "second", "third", "finally", "overall",
]
Rhetoric = dict[str, list[str]]
RHETORIC_MARKERS: Rhetoric = {
    "claim": ["we argue", "i argue", "this suggests", "this shows", "therefore", "thus", "hence"],
    "evidence": ["for example", "for instance", "according to", "data show", "evidence", "study", "report", "survey"],
    "counterpoint": ["however", "yet", "but", "on the other hand", "nevertheless", "nonetheless"],
    "concession": ["although", "though", "even though", "while", "granted", "admittedly"],
    "synthesis": ["overall", "in sum", "in short", "on balance", "taken together", "in conclusion"],
}


def clean_markdown(text: str) -> str:
    text = text.lstrip("\ufeff")
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            text = text[end + 4 :]
    text = HTML_COMMENT_RE.sub(" ", text)
    text = FENCE_RE.sub(" ", text)
    text = INLINE_CODE_RE.sub(" ", text)
    text = IMAGE_RE.sub(" ", text)
    text = LINK_RE.sub(r"\1", text)
    text = BLOCKQUOTE_RE.sub("", text)
    text = HEADING_RE.sub("", text)
    text = LIST_RE.sub("", text)
    text = HTML_TAG_RE.sub(" ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def words(text: str) -> list[str]:
    return WORD_RE.findall(text)


def split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def split_sentences(text: str) -> list[str]:
    # Keep this deterministic and dependency-free. It is intentionally approximate.
    protected = text
    for abbr in ("e.g.", "i.e.", "Mr.", "Mrs.", "Dr.", "vs.", "etc."):
        protected = protected.replace(abbr, abbr.replace(".", "\x00"))
    parts = re.split(r"(?<=[.!?])\s+(?=\S)", protected)
    return [p.replace("\x00", ".").strip() for p in parts if p.strip()]


def _safe_mean(values: Sequence[float]) -> float:
    return float(statistics.mean(values)) if values else 0.0


def _safe_stdev(values: Sequence[float]) -> float:
    return float(statistics.pstdev(values)) if len(values) > 1 else 0.0


def _hist(values: Sequence[int], bins: Sequence[tuple[int, int | None]]) -> list[float]:
    if not values:
        return [0.0 for _ in bins]
    counts: list[int] = []
    for low, high in bins:
        if high is None:
            counts.append(sum(1 for v in values if v >= low))
        else:
            counts.append(sum(1 for v in values if low <= v <= high))
    total = max(1, sum(counts))
    return [c / total for c in counts]


def _rate(count: int | float, total_words: int) -> float:
    return round(1000.0 * float(count) / max(1, total_words), 4)


def _contains_phrase(text: str, phrase: str) -> bool:
    return re.search(r"\b" + re.escape(phrase) + r"\b", text, flags=re.I) is not None


def _ngram_repeat_rate(tokens: list[str], n: int, min_count: int = 3) -> float:
    grams = [tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]
    if not grams:
        return 0.0
    counts = Counter(grams)
    repeated = sum(c for c in counts.values() if c >= min_count)
    return repeated / len(grams)


def _top_phrases(tokens: list[str], n: int, limit: int = 15) -> list[dict[str, int | str]]:
    stop = set(FUNCTION_WORDS)
    grams = []
    for i in range(len(tokens) - n + 1):
        gram = tokens[i : i + n]
        if sum(1 for t in gram if t in stop) >= n - 1:
            continue
        grams.append(tuple(gram))
    return [
        {"phrase": " ".join(g), "count": c}
        for g, c in Counter(grams).most_common(limit)
    ]


def measure_text(text: str, *, clean: bool = True) -> dict:
    prose = clean_markdown(text) if clean else text.strip()
    token_raw = words(prose)
    tokens = [t.lower().replace("’", "'") for t in token_raw]
    total_words = len(tokens)
    paragraphs = split_paragraphs(prose)
    sentences = [s for p in paragraphs for s in split_sentences(p)] if paragraphs else split_sentences(prose)
    sent_lens = [len(words(s)) for s in sentences]
    para_lens = [len(split_sentences(p)) for p in paragraphs]

    punct_counts = {
        "commas": prose.count(","),
        "semicolons": prose.count(";"),
        "colons": prose.count(":"),
        "exclamations": prose.count("!"),
        "questions": prose.count("?"),
        "parentheses_open": prose.count("("),
        "em_dashes": prose.count("—"),
        "en_dashes": prose.count("–"),
        "ellipses": prose.count("…") + prose.count("..."),
    }

    function_counts = Counter(tokens)
    function_rates = {fw: _rate(function_counts.get(fw, 0), total_words) for fw in FUNCTION_WORDS}

    hedge_hits = sum(1 for t in tokens if t in HEDGES)
    booster_hits = sum(1 for t in tokens if t in BOOSTERS)
    directive_hits = sum(1 for t in tokens if t in DIRECTIVES)
    first_hits = sum(1 for t in tokens if t in FIRST_PERSON)
    second_hits = sum(1 for t in tokens if t in SECOND_PERSON)
    third_hits = sum(1 for t in tokens if t in THIRD_PERSON)

    transition_start = 0
    transition_mid = 0
    for sentence in sentences:
        low = sentence.lower().strip()
        matched_start = False
        for marker in TRANSITIONS:
            if low == marker or low.startswith(marker + " ") or low.startswith(marker + ","):
                transition_start += 1
                matched_start = True
                break
        if not matched_start and any(_contains_phrase(low, marker) for marker in TRANSITIONS):
            transition_mid += 1

    rhetorical: dict[str, float] = {}
    for name, markers in RHETORIC_MARKERS.items():
        count = sum(1 for sentence in sentences if any(_contains_phrase(sentence.lower(), m) for m in markers))
        rhetorical[f"{name}_rate"] = _rate(count, total_words)
    evidence = rhetorical.get("evidence_rate", 0.0)
    rhetorical["claim_evidence_ratio"] = round(
        rhetorical.get("claim_rate", 0.0) / evidence, 4
    ) if evidence else 0.0

    opening_lens: list[int] = []
    closing_lens: list[int] = []
    for p in paragraphs:
        ps = split_sentences(p)
        if ps:
            opening_lens.append(len(words(ps[0])))
            closing_lens.append(len(words(ps[-1])))

    contraction_hits = len(re.findall(r"\b[A-Za-z]+(?:n't|'re|'ve|'ll|'d|'m|'s)\b", prose))
    appositive_hits = len(re.findall(r",\s+(?:a|an|the|which|who|that)\b", prose, flags=re.I))
    subordinator_hits = sum(1 for t in tokens if t in SUBORDINATORS)

    sentence_bins = [(0, 9), (10, 17), (18, 25), (26, 40), (41, None)]
    paragraph_bins = [(1, 1), (2, 3), (4, 5), (6, 8), (9, None)]

    return {
        "totals": {
            "words": total_words,
            "sentences": len(sentences),
            "paragraphs": len(paragraphs),
        },
        "sentence": {
            "length_words": {
                "mean": round(_safe_mean(sent_lens), 4),
                "stdev": round(_safe_stdev(sent_lens), 4),
                "histogram_bins": ["<10", "10-17", "18-25", "26-40", ">40"],
                "histogram_p": _hist(sent_lens, sentence_bins),
            }
        },
        "paragraph": {
            "length_sentences_histogram_bins": ["1", "2-3", "4-5", "6-8", ">8"],
            "length_sentences_histogram_p": _hist(para_lens, paragraph_bins),
            "one_sentence_paragraph_rate": (
                sum(1 for n in para_lens if n == 1) / len(para_lens) if para_lens else 0.0
            ),
        },
        "punctuation": {
            "counts": punct_counts,
            "rates_per_1000w": {k: _rate(v, total_words) for k, v in punct_counts.items()},
        },
        "orthography": {
            "contractions_rate_per_1000w": _rate(contraction_hits, total_words),
        },
        "function_words": {"rates_per_1000w": function_rates},
        "stance": {
            "hedge_rate": _rate(hedge_hits, total_words),
            "booster_rate": _rate(booster_hits, total_words),
            "directive_rate": _rate(directive_hits, total_words),
            "first_person_rate": _rate(first_hits, total_words),
            "second_person_rate": _rate(second_hits, total_words),
            "third_person_rate": _rate(third_hits, total_words),
        },
        "transitions": {
            "start_rate_per_1000w": _rate(transition_start, total_words),
            "mid_rate_per_1000w": _rate(transition_mid, total_words),
        },
        "rhetoric": rhetorical,
        "paragraph_cadence": {
            "opening_sentence_length_mean": round(_safe_mean(opening_lens), 4),
            "opening_sentence_length_stdev": round(_safe_stdev(opening_lens), 4),
            "closing_sentence_length_mean": round(_safe_mean(closing_lens), 4),
            "closing_sentence_length_stdev": round(_safe_stdev(closing_lens), 4),
        },
        "syntax": {
            "subordinator_rate": _rate(subordinator_hits, total_words),
            "parenthetical_rate": _rate(prose.count("("), total_words),
            "appositive_rate": _rate(appositive_hits, total_words),
        },
        "repetition": {
            "bigram_repeat_rate": round(_ngram_repeat_rate(tokens, 2), 6),
            "trigram_repeat_rate": round(_ngram_repeat_rate(tokens, 3), 6),
        },
        "common_phrases": {
            "bigrams_top": _top_phrases(tokens, 2),
            "trigrams_top": _top_phrases(tokens, 3),
        },
    }


def profile_documents(documents: Sequence[tuple[str, str]]) -> dict:
    rows = []
    cleaned: list[str] = []
    for doc_id, text in documents:
        prose = clean_markdown(text)
        cleaned.append(prose)
        rows.append({"id": doc_id, "metrics": measure_text(prose, clean=False)})
    aggregate = measure_text("\n\n".join(cleaned), clean=False)
    return {
        "schema_version": 1,
        "documents": rows,
        "aggregate": aggregate,
        "notes": [
            "Document-level metrics are retained so evaluation can use within-author variation rather than a single corpus mean."
        ],
    }


def profile_paths(paths: Iterable[str | Path]) -> dict:
    docs: list[tuple[str, str]] = []
    for path_like in paths:
        path = Path(path_like)
        docs.append((str(path), path.read_text("utf-8", errors="replace")))
    return profile_documents(docs)

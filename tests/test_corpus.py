import json

from twentyfour_myself.corpus import CorpusStore
from twentyfour_myself.models import Document, Message


def test_corpus_deduplicates(tmp_path):
    store = CorpusStore(tmp_path / "corpus")
    records = [
        Message(source="x", external_id="1", text="a"),
        Document(source="x", external_id="2", title="doc", content="b"),
    ]
    first = store.append(records)
    second = store.append(records)
    assert first.added == 2
    assert second.duplicates == 2
    manifest = json.loads(store.manifest_path.read_text(encoding="utf-8"))
    assert manifest["record_counts"] == {"message": 1, "document": 1, "attachment": 0}

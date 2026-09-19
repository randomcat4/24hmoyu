from twentyfour_myself.corpus import CorpusStore
from twentyfour_myself.models import Message


def test_corpus_appends_changed_revision_but_not_exact_repeat(
    tmp_path,
):
    store = CorpusStore(tmp_path)

    first = store.append(
        [
            Message(
                source="x",
                external_id="1",
                text="old",
            )
        ]
    )
    repeat = store.append(
        [
            Message(
                source="x",
                external_id="1",
                text="old",
            )
        ]
    )
    update = store.append(
        [
            Message(
                source="x",
                external_id="1",
                text="new",
            )
        ]
    )

    assert first.added == 1
    assert repeat.duplicates == 1
    assert update.updated == 1
    assert len(list(store.iter_events())) == 2

    current = list(store.iter_records())
    assert len(current) == 1
    assert current[0].text == "new"

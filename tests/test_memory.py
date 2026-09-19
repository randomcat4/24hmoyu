from twentyfour_myself.corpus import CorpusStore
from twentyfour_myself.memory import (
    DreamEngine,
    MemoryAction,
    MemoryOperation,
    MemoryStore,
)
from twentyfour_myself.models import Message


def test_memory_create_update_delete(tmp_path):
    store = MemoryStore(tmp_path)
    created = store.apply_operations(
        [
            MemoryOperation(
                action=MemoryAction.CREATE,
                kind="project",
                content="Project A uses Python",
                source_refs=["x:message:1"],
            )
        ]
    )[0]

    assert store.get(created.id).content == "Project A uses Python"

    store.apply_operations(
        [
            MemoryOperation(
                action=MemoryAction.UPDATE,
                id=created.id,
                kind="project",
                content="Project A uses Python 3.13",
                source_refs=["x:message:2"],
            )
        ]
    )

    current = store.get(created.id)
    assert current.content.endswith("3.13")
    assert current.source_refs == [
        "x:message:1",
        "x:message:2",
    ]

    store.apply_operations(
        [
            MemoryOperation(
                action=MemoryAction.DELETE,
                id=created.id,
            )
        ]
    )
    assert store.get(created.id) is None


def test_dream_checkpoint_moves_only_after_apply(tmp_path):
    corpus = CorpusStore(tmp_path)
    corpus.append(
        [
            Message(
                source="x",
                external_id="1",
                text="We decided Project A uses Python",
            )
        ]
    )
    memory = MemoryStore(tmp_path)

    class FakeModel:
        def consolidate(self, records, existing):
            return [
                MemoryOperation(
                    action=MemoryAction.CREATE,
                    kind="decision",
                    content="Project A uses Python",
                    source_refs=[
                        records[0].stable_key
                    ],
                )
            ]

    engine = DreamEngine(
        corpus,
        memory,
        FakeModel(),
    )

    dry = engine.run(dry_run=True)
    assert dry.processed_records == 1
    assert (
        memory.get_state(
            DreamEngine.STATE_KEY,
            "0",
        )
        == "0"
    )

    done = engine.run()
    assert done.applied == 1
    assert int(
        memory.get_state(
            DreamEngine.STATE_KEY,
            "0",
        )
    ) > 0

    again = engine.run()
    assert again.processed_records == 0



def test_memory_search_miss_returns_empty(tmp_path):
    store = MemoryStore(tmp_path)
    store.apply_operations(
        [
            MemoryOperation(
                action=MemoryAction.CREATE,
                kind="project",
                content="Project A uses Python",
                source_refs=["x:message:1"],
            )
        ]
    )

    assert store.search("完全无关的主题") == []


def test_dream_rejects_hallucinated_source_ref(tmp_path):
    corpus = CorpusStore(tmp_path)
    corpus.append(
        [
            Message(
                source="x",
                external_id="1",
                text="Project A uses Python",
            )
        ]
    )
    memory = MemoryStore(tmp_path)

    class BadModel:
        def consolidate(self, records, existing):
            return [
                MemoryOperation(
                    action=MemoryAction.CREATE,
                    kind="decision",
                    content="Invented",
                    source_refs=["x:message:not-real"],
                )
            ]

    engine = DreamEngine(corpus, memory, BadModel())

    import pytest

    with pytest.raises(ValueError):
        engine.run()

    assert memory.list() == []
    assert memory.get_state(DreamEngine.STATE_KEY, "0") == "0"

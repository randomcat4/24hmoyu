from voicekit.corpus import split_items


def test_split_is_disjoint_and_deterministic():
    items = list(range(20))
    a = split_items(items, seed=7)
    b = split_items(items, seed=7)
    assert a == b
    assert set(a["profile"]).isdisjoint(a["dev"])
    assert set(a["profile"]).isdisjoint(a["final"])
    assert set(a["dev"]).isdisjoint(a["final"])
    assert sorted(a["profile"] + a["dev"] + a["final"]) == items

from hydict import HDict


def test_set_get():
    cache = HDict()

    cache["name"] = "Veeresh"

    assert cache["name"] == "Veeresh"


def test_get_default():
    cache = HDict()

    assert cache.get("missing") is None
    assert cache.get("missing", "default") == "default"


def test_contains():
    cache = HDict()

    cache["name"] = "Veeresh"

    assert "name" in cache
    assert "age" not in cache


def test_delete():
    cache = HDict()

    cache["name"] = "Veeresh"

    del cache["name"]

    assert "name" not in cache


def test_length():
    cache = HDict()

    cache["a"] = 1
    cache["b"] = 2

    assert len(cache) == 2


def test_clear():
    cache = HDict()

    cache["a"] = 1
    cache["b"] = 2

    cache.clear()

    assert len(cache) == 0

def test_hdict_max_entries():
    cache = HDict(max_entries=2)

    cache["A"] = 1
    cache["B"] = 2
    cache["C"] = 3

    assert "A" not in cache
    assert "B" in cache
    assert "C" in cache


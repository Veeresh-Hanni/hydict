import time

import pytest

from hydict.backends.memory import MemoryBackend


def test_memory_set_get():
    backend = MemoryBackend()

    backend.set("name", "Veeresh")

    assert backend.get("name") == "Veeresh"


def test_memory_exists():
    backend = MemoryBackend()

    backend.set("name", "Veeresh")

    assert backend.exists("name")


def test_memory_missing_key():
    backend = MemoryBackend()

    with pytest.raises(KeyError):
        backend.get("missing")


def test_memory_delete():
    backend = MemoryBackend()

    backend.set("name", "Veeresh")
    backend.delete("name")

    assert not backend.exists("name")


def test_memory_len():
    backend = MemoryBackend()

    backend.set("a", 1)
    backend.set("b", 2)

    assert len(backend) == 2


def test_memory_clear():
    backend = MemoryBackend()

    backend.set("a", 1)
    backend.set("b", 2)

    backend.clear()

    assert len(backend) == 0


def test_memory_value_expires():
    backend = MemoryBackend()

    backend.set("name", "Veeresh", ttl=0.1)

    assert backend.get("name") == "Veeresh"

    time.sleep(0.2)

    assert not backend.exists("name")


def test_memory_value_without_ttl_does_not_expire():
    backend = MemoryBackend()

    backend.set("name", "Veeresh")

    time.sleep(0.1)

    assert backend.get("name") == "Veeresh"
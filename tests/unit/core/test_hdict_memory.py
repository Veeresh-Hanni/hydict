from hydict.backends import MemoryBackend


def test_memory_backend_stores_values():
    backend = MemoryBackend()

    backend.set("name", "Veeresh")

    assert backend.get("name") == "Veeresh"
    assert backend.exists("name")
    assert len(backend) == 1


def test_memory_backend_deletes_values():
    backend = MemoryBackend()
    backend.set("name", "Veeresh")

    backend.delete("name")

    assert not backend.exists("name")

import time

from hydict.backends import MemoryBackend


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

import time

from hydict.backends.memory import MemoryBackend


def test_lru_and_ttl_work_together():
    backend = MemoryBackend(max_entries=2)

    backend.set("A", 1, ttl=0.1)
    backend.set("B", 2)

    time.sleep(0.2)

    backend.set("C", 3)

    assert not backend.exists("A")
    assert backend.exists("B")
    assert backend.exists("C")

def test_access_updates_lru_order():
    backend = MemoryBackend(max_entries=3)

    backend.set("A", 1)
    backend.set("B", 2)
    backend.set("C", 3)

    # Make A recently used
    assert backend.get("A") == 1

    # B should now be the oldest
    backend.set("D", 4)

    assert backend.exists("A")
    assert not backend.exists("B")
    assert backend.exists("C")
    assert backend.exists("D")

def test_update_existing_key_refreshes_lru():
    backend = MemoryBackend(max_entries=3)

    backend.set("A", 1)
    backend.set("B", 2)
    backend.set("C", 3)

    backend.set("A", 100)

    backend.set("D", 4)

    assert backend.get("A") == 100
    assert not backend.exists("B")
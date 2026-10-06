import threading

from hydict.backends.memory import MemoryBackend


def test_oldest_entry_is_evicted():
    backend = MemoryBackend(max_entries=3)

    backend.set("A", 1)
    backend.set("B", 2)
    backend.set("C", 3)
    backend.set("D", 4)

    assert not backend.exists("A")
    assert backend.exists("B")
    assert backend.exists("C")
    assert backend.exists("D")

import time

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

    # A becomes recently used
    assert backend.get("A") == 1

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

    # Updating A makes it recently used
    backend.set("A", 100)

    backend.set("D", 4)

    assert backend.get("A") == 100
    assert not backend.exists("B")
    assert backend.exists("C")
    assert backend.exists("D")

def test_concurrent_lru_operations():
    backend = MemoryBackend(max_entries=10)

    def worker(thread_id):
        for i in range(100):
            key = f"{thread_id}-{i}"
            backend.set(key, i)
            backend.exists(key)
            backend.get(key)

    threads = [
        threading.Thread(target=worker, args=(i,))
        for i in range(5)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    assert len(backend) <= 10
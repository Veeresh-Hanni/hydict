import threading

from hydict.backends.memory import MemoryBackend
from hydict import RedisConfig

def test_concurrent_writes():
    backend = MemoryBackend()

    def write_value(value):
        for _ in range(1000):
            backend.set("counter", value)

    threads = [
        threading.Thread(target=write_value, args=(1,)),
        threading.Thread(target=write_value, args=(2,)),
        threading.Thread(target=write_value, args=(3,)),
        threading.Thread(target=write_value, args=(4,)),
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    assert backend.get("counter") in {1, 2, 3, 4}

from hydict import HDict


def test_concurrent_hdict_writes():
    cache = HDict(max_entries=10)

    def worker(thread_id):
        for i in range(100):
            key = f"{thread_id}-{i}"
            cache[key] = i

    threads = [
        threading.Thread(target=worker, args=(i,))
        for i in range(5)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    assert len(cache._memory) <= 10

def test_concurrent_reads():
    cache = HDict(max_entries=100)

    for i in range(100):
        cache[i] = i

    def worker():
        for i in range(100):
            assert cache[i] == i

    threads = [
        threading.Thread(target=worker)
        for _ in range(10)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

def test_concurrent_reads_and_writes():
    cache = HDict(max_entries=50)

    for i in range(50):
        cache[i] = i

    errors = []

    def reader():
        for i in range(1000):
            try:
                cache[i % 50]
            except KeyError:
                pass
            except Exception as e:
                errors.append(e)

    def writer():
        for i in range(1000):
            cache[i % 50] = i

    threads = []

    for _ in range(5):
        threads.append(threading.Thread(target=reader))

    for _ in range(5):
        threads.append(threading.Thread(target=writer))

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    assert errors == []

def test_concurrent_get_and_delete():
    cache = HDict(max_entries=10)

    cache["user"] = "Veeresh"

    errors = []

    def reader():
        for _ in range(1000):
            try:
                cache["user"]
            except KeyError:
                pass
            except Exception as e:
                errors.append(e)

    def deleter():
        for _ in range(1000):
            cache["user"] = "Veeresh"
            try:
                del cache["user"]
            except KeyError:
                pass

    threads = [
        threading.Thread(target=reader)
        for _ in range(5)
    ]

    threads += [
        threading.Thread(target=deleter)
        for _ in range(5)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    assert errors == []

def test_concurrent_writes_respect_lru_limit():
    cache = HDict(max_entries=5)

    def worker(thread_id):
        for i in range(100):
            cache[f"{thread_id}-{i}"] = i

    threads = [
        threading.Thread(target=worker, args=(i,))
        for i in range(10)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    assert len(cache._memory) <= 5

def test_concurrent_redis_access():
    config = RedisConfig(
        db=15,
        max_connections=5,
        pool_timeout=5
    )

    cache = HDict(config, max_entries=100)

    errors = []

    def worker(thread_id):
        try:
            for i in range(100):
                key = f"thread-{thread_id}-{i}"

                cache[key] = i

                assert cache[key] == i
                assert key in cache

        except Exception as exc:
            errors.append(exc)

    threads = [
        threading.Thread(target=worker, args=(i,))
        for i in range(10)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    assert errors == []


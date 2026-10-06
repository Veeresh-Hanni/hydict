import os
import threading
import time

import pytest

from hydict.config.redis import RedisConfig
from hydict.stampede import StampedeProtection
from hydict import HDict

def test_same_key_returns_same_lock():
    protection = StampedeProtection()

    lock1 = protection.get_lock("user:1")
    lock2 = protection.get_lock("user:1")

    assert lock1 is lock2

def test_different_keys_have_different_locks():
    protection = StampedeProtection()

    lock1 = protection.get_lock("user:1")
    lock2 = protection.get_lock("user:2")

    assert lock1 is not lock2

def test_get_or_set_loader_called_only_once():
    cache = HDict()

    calls = 0
    calls_lock = threading.Lock()

    def loader():
        nonlocal calls

        with calls_lock:
            calls += 1

        time.sleep(0.1)

        return "Veeresh"

    results = []

    def worker():
        value = cache.get_or_set("name", loader)
        results.append(value)

    threads = [
        threading.Thread(target=worker)
        for _ in range(10)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    assert calls == 1
    assert results == ["Veeresh"] * 10

def test_get_or_set_calls_loader_on_cache_miss():
    cache = HDict()

    calls = 0

    def loader():
        nonlocal calls
        calls += 1
        return "Veeresh"

    result = cache.get_or_set("name", loader)

    assert result == "Veeresh"
    assert calls == 1
    assert cache["name"] == "Veeresh"

def test_get_or_set_does_not_call_loader_on_cache_hit():
    cache = HDict()

    cache["name"] = "Veeresh"

    calls = 0

    def loader():
        nonlocal calls
        calls += 1
        return "Rahul"

    result = cache.get_or_set("name", loader)

    assert result == "Veeresh"
    assert calls == 0

def test_get_or_set_loader_exception_releases_lock():
    cache = HDict()
    calls = 0

    def failing_loader():
        nonlocal calls
        calls += 1
        raise ValueError("database failed")

    with pytest.raises(ValueError):
        cache.get_or_set("user:1", failing_loader)

    # The lock must have been released so another attempt can retry.
    result = cache.get_or_set(
        "user:1",
        lambda: "Veeresh",
    )

    assert result == "Veeresh"
    assert calls == 1

def test_get_or_set_respects_ttl():
    cache = HDict()

    result = cache.get_or_set(
        "name",
        lambda: "Veeresh",
        ttl=2,
    )

    assert result == "Veeresh"

    value, ttl = cache._memory.get_with_ttl("name")

    assert value == "Veeresh"
    assert ttl > 0
    assert ttl <= 2

@pytest.mark.skipif(
    os.getenv("HYDICT_REDIS_INTEGRATION") != "1",
    reason="set HYDICT_REDIS_INTEGRATION=1 to run Redis integration tests",
)
def test_get_or_set_uses_l2_before_loader():
    cache = HDict(RedisConfig())

    cache.set("name", "Veeresh")

    # Force L1 miss while keeping the Redis value.
    cache._memory.delete("name")

    calls = 0

    def loader():
        nonlocal calls
        calls += 1
        return "Rahul"

    result = cache.get_or_set("name", loader)

    assert result == "Veeresh"
    assert calls == 0

import time

import pytest

from hydict.backends.memory import MemoryBackend
from hydict.config.redis import RedisConfig
from hydict.core.hdict import HDict
from hydict.invalidation import CacheInvalidator

class FakeRedis:

    def __init__(self, **kwargs):
        self.values = {}
        self.expiry = {}
        self.kwargs = kwargs
        

    def set(self, key, value, ex=None):
        self.values[key] = value

        if ex is not None:
            self.expiry[key] = time.monotonic() + ex
        else:
            self.expiry.pop(key, None)

    def get(self, key):
        self._remove_if_expired(key)
        return self.values.get(key)

    def ttl(self, key):
        self._remove_if_expired(key)

        if key not in self.values:
            return -2

        if key not in self.expiry:
            return -1

        remaining = self.expiry[key] - time.monotonic()

        return max(0, int(remaining))

    def delete(self, key):
        self.values.pop(key, None)
        self.expiry.pop(key, None)

    def exists(self, key):
        self._remove_if_expired(key)
        return int(key in self.values)

    def flushdb(self):
        self.values.clear()
        self.expiry.clear()

    def _remove_if_expired(self, key):
        expiry = self.expiry.get(key)

        if expiry is not None and time.monotonic() >= expiry:
            self.values.pop(key, None)
            self.expiry.pop(key, None)
    def dbsize(self):
        self._remove_expired()
        return len(self.values)
    
    def _remove_expired(self):
        for key in list(self.expiry):
            self._remove_if_expired(key)


def test_invalidate_removes_key_from_both_layers():
    l1 = MemoryBackend()
    l2 = MemoryBackend()

    l1.set("name", "Veeresh")
    l2.set("name", "Veeresh")

    invalidator = CacheInvalidator(l1, l2)

    invalidator.invalidate("name")

    assert not l1.exists("name")
    assert not l2.exists("name")

def test_invalidate_missing_key_is_safe():
    l1 = MemoryBackend()
    l2 = MemoryBackend()

    invalidator = CacheInvalidator(l1, l2)

    invalidator.invalidate("missing")

    assert not l1.exists("missing")
    assert not l2.exists("missing")

def test_hdict_invalidate_removes_from_both_layers(monkeypatch):
    monkeypatch.setattr(
        "hydict.backends.remote.redis.Redis",
        FakeRedis,
    )

    cache = HDict(RedisConfig())

    cache["name"] = "Veeresh"

    assert cache._memory.exists("name")
    assert cache._remote.exists("name")

    cache.invalidate("name")

    assert not cache._memory.exists("name")
    assert not cache._remote.exists("name")

def test_hdict_invalidate_without_l2():
    cache = HDict()

    cache["name"] = "Veeresh"

    assert cache._memory.exists("name")

    cache.invalidate("name")

    assert not cache._memory.exists("name")
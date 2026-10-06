import os

import pytest
import redis

from hydict.backends import Backend
from hydict.backends.remote import RemoteBackend
from hydict.config import RedisConfig
from hydict.core import HDict

from redis.exceptions import ConnectionError as RedisConnectionError

from hydict.exceptions import (
    BackendConnectionError,
    BackendOperationError,
)

import time


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


def test_l2_hit_promotes_to_l1(monkeypatch):
    monkeypatch.setattr(
        "hydict.backends.remote.redis.Redis",
        FakeRedis
    )

    cache = HDict(RedisConfig())

    cache["name"] = "Veeresh"

    # Both L1 and L2 contain the value
    assert cache._memory.exists("name")
    assert cache._remote.exists("name")

    # Remove only L1
    cache._memory.clear()

    # L1 MISS, L2 HIT
    assert not cache._memory.exists("name")
    assert cache._remote.exists("name")

    # HDict must get from L2 and promote to L1
    assert cache["name"] == "Veeresh"

    # Verify promotion
    assert cache._memory.exists("name")
    assert cache._memory.get("name") == "Veeresh"

def test_l1_l2_miss():
    cache = HDict()

    with pytest.raises(KeyError) as exc:
        cache["name"]

    assert exc.value.args[0] == "name"

class BrokenRedis:

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def set(self, key, value):
        raise RedisConnectionError("Redis unavailable")

    def get(self, key):
        raise RedisConnectionError("Redis unavailable")

    def delete(self, key):
        raise RedisConnectionError("Redis unavailable")

    def exists(self, key):
        raise RedisConnectionError("Redis unavailable")

    def flushdb(self):
        raise RedisConnectionError("Redis unavailable")

def test_remote_backend_translates_connection_error(monkeypatch):
    monkeypatch.setattr(
        "hydict.backends.remote.redis.Redis",
        BrokenRedis
    )

    backend = RemoteBackend(RedisConfig())

    with pytest.raises(BackendConnectionError):
        backend.set("name", "Veeresh")

class FailedRedis:

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def set(self, key, value):
        raise redis.RedisError("Redis operation failed")

    def get(self, key):
        raise redis.RedisError("Redis operation failed")

    def delete(self, key):
        raise redis.RedisError("Redis operation failed")

    def exists(self, key):
        raise redis.RedisError("Redis operation failed")

    def flushdb(self):
        raise redis.RedisError("Redis operation failed")

def test_remote_backend_translates_operation_error(monkeypatch):
    monkeypatch.setattr(
        "hydict.backends.remote.redis.Redis",
        FailedRedis
    )

    backend = RemoteBackend(RedisConfig())

    with pytest.raises(BackendOperationError):
        backend.set("name", "Veeresh")

def test_remote_backend_serializes_dict(monkeypatch):
    monkeypatch.setattr(
        "hydict.backends.remote.redis.Redis",
        FakeRedis
    )

    backend = RemoteBackend(RedisConfig())

    value = {
        "name": "Veeresh",
        "age": 20,
        "skills": ["Python", "Django"],
    }

    backend.set("user", value)

    assert backend.client.values["user"] == (
        '{"name": "Veeresh", "age": 20, "skills": ["Python", "Django"]}'
    )

    assert backend.get("user") == value

def test_l2_dict_hit_promotes_to_l1(monkeypatch):
    monkeypatch.setattr(
        "hydict.backends.remote.redis.Redis",
        FakeRedis
    )

    cache = HDict(RedisConfig())

    value = {
        "name": "Veeresh",
        "skills": ["Python", "Django"],
    }

    cache["user"] = value

    cache._memory.clear()

    assert not cache._memory.exists("user")
    assert cache._remote.exists("user")

    result = cache["user"]

    assert result == value

    assert cache._memory.exists("user")
    assert cache._memory.get("user") == value

def test_remote_backend_ttl(monkeypatch):
    monkeypatch.setattr(
        "hydict.backends.remote.redis.Redis",
        FakeRedis
    )

    backend = RemoteBackend(RedisConfig())

    backend.set("name", "Veeresh", ttl=1)

    assert backend.get("name") == "Veeresh"
    assert backend.client.ttl("name") >= 0

def test_hdict_ttl_expires_from_l1(monkeypatch):
    monkeypatch.setattr(
        "hydict.backends.remote.redis.Redis",
        FakeRedis
    )

    cache = HDict(RedisConfig())

    cache.set("name", "Veeresh", ttl=0.1)

    assert cache["name"] == "Veeresh"

    time.sleep(0.2)

    with pytest.raises(KeyError):
        cache["name"]

def test_l2_hit_preserves_ttl_in_l1(monkeypatch):
    monkeypatch.setattr(
        "hydict.backends.remote.redis.Redis",
        FakeRedis
    )

    cache = HDict(RedisConfig())

    cache.set("name", "Veeresh", ttl=2)

    cache._memory.clear()

    assert not cache._memory.exists("name")
    assert cache._remote.exists("name")

    assert cache["name"] == "Veeresh"

    assert cache._memory.exists("name")

def test_remote_backend_implements_backend(monkeypatch):
    monkeypatch.setattr(
        "hydict.backends.remote.redis.Redis",
        FakeRedis,
    )

    backend = RemoteBackend(RedisConfig())

    assert isinstance(backend, Backend)

def test_remote_backend_uses_cache_config(monkeypatch):
    monkeypatch.setattr("hydict.backends.remote.redis.Redis", FakeRedis)

    config = RedisConfig(
        host="redis.example",
        port=6380,
    )

    backend = RemoteBackend(config)

    backend.set("name", "Veeresh")

    assert backend.get("name") == "Veeresh"

    pool = backend.client.kwargs["connection_pool"]

    assert pool.connection_kwargs["host"] == "redis.example"
    assert pool.connection_kwargs["port"] == 6380

@pytest.mark.skipif(
    os.getenv("HYDICT_REDIS_INTEGRATION") != "1",
    reason="set HYDICT_REDIS_INTEGRATION=1 to run Redis integration tests",
)
def test_remote_backend_pool_exhaustion_translates_connection_error():
    config = RedisConfig(
        max_connections=1,
        pool_timeout=None,
    )

    backend = RemoteBackend(config)

    pool = backend.client.connection_pool

    connection = pool.get_connection("SET")

    try:
        with pytest.raises(BackendConnectionError):
            backend.set("name", "Veeresh")
    finally:
        pool.release(connection)

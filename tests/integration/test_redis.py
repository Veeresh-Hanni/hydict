import os
import time

import pytest

from hydict import HDict
from hydict.config import RedisConfig


pytestmark = pytest.mark.skipif(
    os.getenv("HYDICT_REDIS_INTEGRATION") != "1",
    reason="set HYDICT_REDIS_INTEGRATION=1 to run Redis integration tests",
)


@pytest.fixture
def cache():
    cache = HDict(RedisConfig(db=15))
    cache.clear()
    yield cache
    cache.clear()


def test_redis_set_get(cache):
    cache["name"] = "Veeresh"

    assert cache["name"] == "Veeresh"


def test_redis_delete(cache):
    cache["name"] = "Veeresh"

    assert cache["name"] == "Veeresh"

    del cache["name"]

    with pytest.raises(KeyError):
        cache["name"]


def test_redis_contains(cache):
    cache["name"] = "Veeresh"

    assert "name" in cache

    del cache["name"]

    assert "name" not in cache


def test_redis_clear(cache):
    cache["a"] = 1
    cache["b"] = 2

    cache.clear()

    assert "a" not in cache
    assert "b" not in cache


def test_redis_l2_promotes_to_l1(cache):
    cache["name"] = "Veeresh"

    # Confirm value exists in L2.
    assert cache._remote.exists("name")

    # Remove only L1.
    cache._memory.clear()

    assert not cache._memory.exists("name")
    assert cache._remote.exists("name")

    # This must fetch from Redis.
    assert cache["name"] == "Veeresh"

    # Redis value should now be promoted back to L1.
    assert cache._memory.exists("name")
    assert cache._memory.get("name") == "Veeresh"


def test_redis_missing_key(cache):
    with pytest.raises(KeyError):
        cache["missing"]

def test_redis_ttl_expires(cache):
    cache.set("name", "Veeresh", ttl=1)

    assert cache["name"] == "Veeresh"

    time.sleep(1.2)

    with pytest.raises(KeyError):
        cache["name"]

def test_redis_ttl_is_set(cache):
    cache.set("name", "Veeresh", ttl=10)

    ttl = cache._remote.client.ttl("name")

    assert 0 < ttl <= 10

def test_redis_l2_promotion_preserves_ttl(cache):
    cache.set("user", {
        "name": "Veeresh",
        "skills": ["Python", "Django"],
    }, ttl=10)

    # Remove L1 only.
    cache._memory.clear()

    assert not cache._memory.exists("user")
    assert cache._remote.exists("user")

    # Fetch from Redis.
    value = cache["user"]

    assert value == {
        "name": "Veeresh",
        "skills": ["Python", "Django"],
    }

    # It must have been promoted to L1.
    assert cache._memory.exists("user")

def test_redis_ttl_expires_from_l1(cache):
    cache.set("name", "Veeresh", ttl=1)

    assert cache["name"] == "Veeresh"

    # Wait for expiration.
    time.sleep(1.2)

    assert not cache._memory.exists("name")

    with pytest.raises(KeyError):
        cache["name"]

def test_redis_l1_lru_eviction_and_l2_promotion(cache):
    cache._memory.max_entries = 2

    cache["A"] = 1
    cache["B"] = 2
    cache["C"] = 3

    # L1 should only contain the two most recent keys.
    assert not cache._memory.exists("A")
    assert cache._memory.exists("B")
    assert cache._memory.exists("C")

    # But A must still exist in L2.
    assert cache._remote.exists("A")

    # Access A -> L1 miss -> L2 hit -> promote to L1.
    assert cache["A"] == 1

    # A is now recent, so B should be evicted.
    assert cache._memory.exists("A")
    assert not cache._memory.exists("B")
    assert cache._memory.exists("C")

    # B must still exist in L2.
    assert cache._remote.exists("B")

def test_redis_l1_lru_with_public_api():
    cache = HDict(
        RedisConfig(db=15),
        max_entries=2,
    )

    cache.clear()

    cache["A"] = 1
    cache["B"] = 2
    cache["C"] = 3

    # L1 has a maximum of 2 entries.
    assert not cache._memory.exists("A")
    assert cache._memory.exists("B")
    assert cache._memory.exists("C")

    # A was evicted from L1 but remains in L2.
    assert cache._remote.exists("A")

    # A should come back from L2 and be promoted to L1.
    assert cache["A"] == 1

    # A is now recently used, so B becomes the LRU entry.
    assert cache._memory.exists("A")
    assert not cache._memory.exists("B")
    assert cache._memory.exists("C")

    # B still exists in L2.
    assert cache._remote.exists("B")

    cache.clear()
import pytest

from hydict.core import HDict
from hydict.metrics import MetricsCollector
from hydict.config import RedisConfig


def test_metrics_start_at_zero():
    metrics = MetricsCollector()

    assert metrics.l1_hits == 0
    assert metrics.l2_hits == 0
    assert metrics.misses == 0
    assert metrics.loader_calls == 0


def test_metrics_record_events():
    metrics = MetricsCollector()

    metrics.record_l1_hit()
    metrics.record_l2_hit()
    metrics.record_miss()
    metrics.record_loader_call()

    assert metrics.l1_hits == 1
    assert metrics.l2_hits == 1
    assert metrics.misses == 1
    assert metrics.loader_calls == 1


def test_hdict_records_l1_hit():
    cache = HDict()
    cache["name"] = "Veeresh"

    assert cache["name"] == "Veeresh"
    assert cache._metrics.l1_hits == 1


def test_hdict_records_miss():
    cache = HDict()

    try:
        cache["missing"]
    except KeyError:
        pass

    assert cache._metrics.misses == 1


def test_hdict_records_loader_call():
    cache = HDict()

    result = cache.get_or_set(
        "name",
        lambda: "Veeresh",
    )

    assert result == "Veeresh"
    assert cache._metrics.loader_calls == 1



def test_hdict_records_l2_hit():
    cache = HDict(RedisConfig())

    cache.set("name", "Veeresh")

    # Remove only L1 so the next read must go to Redis.
    cache._memory.delete("name")

    assert cache["name"] == "Veeresh"

    assert cache._metrics.l1_hits == 0
    assert cache._metrics.l2_hits == 1
    assert cache._metrics.misses == 0

def test_hdict_stats():
    cache = HDict()

    cache["name"] = "Veeresh"

    # L1 hit
    assert cache["name"] == "Veeresh"

    # Miss + loader
    result = cache.get_or_set(
        "city",
        lambda: "Gadag",
    )

    assert result == "Gadag"

    assert cache.stats() == {
        "l1_hits": 1,
        "l2_hits": 0,
        "total_hits": 1,
        "misses": 1,
        "loader_calls": 1,
    }



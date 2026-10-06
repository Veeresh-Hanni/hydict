# hydict

`hydict` is a dict-compatible hierarchical cache for Python. It uses local
in-memory storage as L1 and can use Redis or Valkey as L2.

## Version 0.5.0

Version 0.5.0 is the V5 release. It includes the synchronous cache API,
invalidation, metrics, and per-key stampede protection. V5 release verification
recorded 82 passing tests.

## Features

- Fast, local L1 in-memory cache
- Optional Redis/Valkey L2 cache
- L1 promotion after an L2 cache hit
- TTL support, including TTL preservation during L2-to-L1 promotion
- LRU eviction with an optional `max_entries` limit
- Redis connection pooling
- Thread-safe L1 operations
- Cache invalidation
- Cache statistics
- `get_or_set()` with per-key locking to reduce cache stampedes

## Quick start

```python
from hydict import HDict

cache = HDict(max_entries=100)

cache["name"] = "Veeresh"
assert cache["name"] == "Veeresh"
```

Use `set()` when a value needs a TTL:

```python
cache.set("session:1", {"user_id": 1}, ttl=60)
```

## Redis or Valkey backend

Pass `RedisConfig` to enable L2 storage. A compatible Redis or Valkey server
must be available at the configured address.

```python
from hydict import HDict, RedisConfig

cache = HDict(
    RedisConfig(
        host="localhost",
        port=6379,
        max_connections=10,
    )
)

cache.set("user:1", {"name": "Veeresh"}, ttl=300)
```

Reads check L1 first. On an L1 miss, `HDict` checks L2 and promotes an L2 hit
into L1.

## Loading missing values

`get_or_set()` returns an existing value when present. For a missing key, it
calls the loader, stores the returned value, and returns it. Concurrent callers
for the same key share a per-key lock, so only one loader call populates that
key at a time.

```python
user = cache.get_or_set(
    "user:1",
    lambda: load_user_from_database(),
    ttl=60,
)
```

## Invalidation and metrics

```python
cache.invalidate("user:1")

print(cache.stats())
# {
#     "l1_hits": 0,
#     "l2_hits": 0,
#     "total_hits": 0,
#     "misses": 0,
#     "loader_calls": 0,
# }
```

`invalidate()` removes the key from L1 and, when configured, L2.

## Development

Run the test suite:

```powershell
python -m pip install -e .
pytest -q
```

Redis integration tests are opt-in. Set `HYDICT_REDIS_INTEGRATION=1` before
running the integration test suite with a Redis server available.

## Continuous integration and releases

GitHub Actions runs unit tests for pull requests and runs the complete
`pytest -q` suite against Redis 7 with `HYDICT_REDIS_INTEGRATION=1` for release
validation. Publishing runs only for version tags such as `v0.5.0`, and only
after both test jobs succeed. After a successful PyPI upload, the workflow also
creates a GitHub Release with generated notes and the wheel/source archive
attached.

To enable publishing, create the `PYPI_TOKEN` repository secret with a PyPI API
token. The workflow passes it to Twine without placing the token in the
repository or workflow logs.

## Roadmap

The next planned release is `0.6.0` (V6), which will introduce an asynchronous
API for `asyncio` applications. Async support is not part of version 0.5.0.

See [docs/architecture.md](docs/architecture.md) for cache behavior and design
notes, the [developer guide](docs/developer-guide.md) for API and implementation
details, and [CHANGELOG.md](CHANGELOG.md) for release history.

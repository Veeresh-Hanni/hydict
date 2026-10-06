# hydict developer guide

## 1. Introduction

`hydict` is a synchronous, dict-like hierarchical cache. It gives an
application a fast local cache (L1) and, when configured, a Redis or Valkey
cache (L2). It is useful when repeated reads should usually be served from the
current process, while values may also be retained in a remote cache shared by
other processes.

```text
                  Application
                       |
                       v
                     HDict
                       |
             +---------+---------+
             |                   |
             v                   v
       MemoryBackend        RemoteBackend
          L1 cache          Redis / Valkey L2
             |                   |
       OrderedDict, TTL      connection pool, JSON
```

L1 avoids a network call for hot values. L2 makes a value available after it
has left a process's L1 cache, including after L1 eviction. `hydict` is most
appropriate when the application owns its cache-update and invalidation
strategy; it is not a transactional database or a distributed locking system.

## 2. Installation

Install the published package with:

```bash
pip install hydict
```

L1-only use needs no server. L2 needs a reachable Redis or Valkey server and
uses the `redis` Python package declared by the project.

```python
from hydict import HDict

cache = HDict()
cache["name"] = "Veeresh"
print(cache["name"])
```

## 3. Public API reference

| Public object | Signature | Purpose |
| --- | --- | --- |
| `HDict` | `HDict(config=None, max_entries=None)` | Hierarchical cache facade. |
| `HDict.__getitem__` | `cache[key]` | Read from L1, then L2 when configured. |
| `HDict.__setitem__` | `cache[key] = value` | Store a value without a TTL. |
| `HDict.__delitem__` | `del cache[key]` | Delete from L1 and configured L2. |
| `HDict.__contains__` | `key in cache` | Check L1, then L2 when configured. |
| `HDict.__len__` | `len(cache)` | Return the number of live L1 entries. |
| `HDict.get` | `get(key, default=None)` | Read, returning a default for a missing key. |
| `HDict.set` | `set(key, value, ttl=None)` | Store a value with an optional TTL. |
| `HDict.clear` | `clear()` | Clear L1 and configured L2. |
| `HDict.invalidate` | `invalidate(key)` | Safely remove a key from both layers. |
| `HDict.get_or_set` | `get_or_set(key, loader, ttl=None)` | Read or load one missing key with per-key locking. |
| `HDict.stats` | `stats()` | Return process-local cache counters. |
| `RedisConfig` | `RedisConfig(...)` | Redis/Valkey connection-pool settings. |

There is currently **no** public `HDict.delete()` or `HDict.exists()` method.
Use `del cache[key]` and `key in cache` instead. `MemoryBackend`,
`RemoteBackend`, `Serializer`, `MetricsCollector`, `CacheInvalidator`, and
`StampedeProtection` are implementation components; their APIs are described
below for debugging and extension, not as the primary application API.

### `HDict(config=None, max_entries=None)`

Creates an L1 `MemoryBackend` and, if `config` is not `None`, a
`RemoteBackend`. In normal use, pass a `RedisConfig` instance. `max_entries`
sets the L1 entry limit; `None` means no LRU capacity limit. It exists so an
application can begin with L1-only caching and opt into L2 without changing
its call sites.

```python
from hydict import HDict, RedisConfig

local_cache = HDict(max_entries=1_000)
shared_cache = HDict(RedisConfig(host="localhost", db=0), max_entries=1_000)
```

### Mapping methods

`cache[key]` reads a value. It returns the value on a hit and raises `KeyError`
when neither configured layer has a live value. `cache[key] = value` writes to
L1 and then L2, if present. `del cache[key]` deletes from L1 and then L2; a
missing L1 key raises `KeyError`. `key in cache` checks L1 first, then L2. It
does not promote an L2 value into L1. `len(cache)` counts only unexpired L1
entries; it is not the remote database size.

```python
cache["user:1"] = {"name": "Veeresh"}
user = cache["user:1"]
if "user:1" in cache:
    del cache["user:1"]
```

### `get(key, default=None)`

This is the non-raising lookup. Internally it calls `__getitem__` and converts
only `KeyError` to `default`; Redis/backend errors still propagate. Use it when
a cache miss is an expected branch.

```python
theme = cache.get("theme", "light")
```

### `set(key, value, ttl=None)`

Stores a value in L1 and, if configured, L2. `ttl=None` means no expiry.
Otherwise the L1 backend records an expiry using `time.monotonic()` and L2 is
given the TTL through Redis's native expiry support. Use this instead of
assignment when expiry is required.

```python
cache.set("session:abc", {"user_id": 42}, ttl=60)
```

### `clear()` and `invalidate(key)`

`clear()` clears all L1 entries and flushes the configured remote database.
Because L2 clearing maps to Redis `FLUSHDB`, use it carefully with a shared
database. `invalidate(key)` removes only one key from L1 and L2 and ignores a
missing key. It exists for stale-data removal after the source of truth changes.

```python
cache.invalidate("user:42")
```

### `get_or_set(key, loader, ttl=None)`

Returns a cached value, or runs the zero-argument `loader` once for a missing
key and stores its result. It is intended for expensive work such as a database
query, API request, computation, or file read. It returns the cached or loaded
value. `KeyError` during lookup is handled internally; exceptions raised by the
loader propagate unchanged.

```python
user = cache.get_or_set(
    "user:42",
    lambda: fetch_user_from_database(42),
    ttl=60,
)
```

### `stats()`

Returns a new dictionary of process-local counters:

```python
{
    "l1_hits": 0,
    "l2_hits": 0,
    "total_hits": 0,
    "misses": 0,
    "loader_calls": 0,
}
```

Counters begin at zero when an `HDict` instance is created. They are not shared
across processes and are not persisted in Redis.

## 4. Read flow

For `cache["user:1"]`, `HDict` asks L1 first. A live L1 hit increments
`l1_hits`. On an L1 miss with L2 configured, it calls L2 `get_with_ttl()`.
An L2 hit increments `l2_hits`, is copied into L1 with its remaining TTL, and
is returned. A miss increments `misses` and raises `KeyError`.

```text
cache["user:1"]
       |
       v
      L1
   /       \
 hit       miss
 |          |
return      v
           L2
        /       \
      hit       miss
       |          |
   promote       KeyError
    to L1
       |
     return
```

Promotion lets the next read use memory rather than the network. If L2 says a
value has no expiry (`ttl < 0`), L1 stores it without a TTL. Otherwise L1 uses
the remaining remote TTL, so a promoted value does not outlive its L2 source.

## 5. Write flow and consistency

Assignment is equivalent to an unexpired write:

```python
cache["user:1"] = value
```

`HDict.__setitem__` writes the raw Python value to L1, then calls L2 `set()` if
configured. Remote writes serialize the value as JSON before sending it to
Redis. `set(..., ttl=...)` follows the same order while passing expiry to both
layers.

```text
HDict.set / __setitem__
       |
       +--> L1 set (protected by MemoryBackend's lock)
       |
       +--> L2 set (JSON + Redis call), if configured
```

This is not a distributed transaction. If the L2 write fails, L1 may already
contain the new value and the remote backend error is raised. Concurrent calls
can also observe updates between the L1 and L2 operations. L1 operations are
thread-safe individually; cross-layer consistency is the application's
responsibility.

## 6. `MemoryBackend` (implementation detail)

`MemoryBackend` implements the `Backend` interface for L1. It keeps values in
an `OrderedDict` named `_data` and expiry timestamps in `_expiry`. Every public
operation is protected by an `RLock`, allowing a thread already holding that
lock to re-enter a backend method safely.

- `set(key, value, ttl=None)` stores or replaces a value, moves it to the most
  recently used end, records/removes expiry, then calls `_evict_if_needed()`.
- `get(key)` calls `_remove_if_expired()`, returns the value, and refreshes its
  recency. Missing or expired values raise `KeyError`.
- `get_with_ttl(key)` returns `(value, ttl)`. It uses `-1` for no expiry and an
  integer number of remaining seconds for an expiring item.
- `delete(key)` removes data and expiry metadata; a missing live key raises
  `KeyError`.
- `exists(key)` lazily removes an expired entry and returns a boolean.
- `clear()` removes all data and expiry metadata.
- `__len__()` removes all expired keys before counting L1 entries.

The private helpers `_evict_if_needed()`, `_remove_if_expired(key)`, and
`_remove_expired()` implement capacity enforcement and lazy expiry cleanup.
They are not application-facing APIs.

## 7. LRU eviction

L1 uses `OrderedDict` order as recency order. A successful `get()` or `set()`
moves that key to the end. When adding a value makes `_data` larger than
`max_entries`, `_evict_if_needed()` removes the first (least recent) key.

```text
max_entries = 3

set(A), set(B), set(C)  -> A B C
get(A)                  -> B C A
set(D)                  -> C A D
```

`B` is evicted because it became the oldest key after `A` was read. Eviction
only removes L1 data. With L2 configured, the remote copy is not deleted and a
later read can promote it back to L1.

## 8. TTL

```python
cache.set("user:1", user, ttl=60)
```

L1 records `time.monotonic() + ttl`, which is unaffected by wall-clock changes.
Expiry is enforced lazily when a key is read, checked, deleted, or when L1 is
counted. Redis receives its native `ex=ttl` setting. With `ttl=None`, both
layers store the value without an expiry.

During L2-to-L1 promotion, `RemoteBackend.get_with_ttl()` returns Redis's
remaining TTL and L1 receives that amount:

```text
L2: user:1 -> value, remaining TTL = 42 seconds
                         |
                         v
L1: user:1 -> value, TTL approximately 42 seconds
```

This prevents an L2 hit from extending the value's life merely because it was
read. Once expired, a lookup behaves as a miss. TTLs are not refreshed by a
read.

## 9. `RemoteBackend` and `RedisConfig`

`RemoteBackend` is the L2 `Backend` implementation. It creates a `redis.Redis`
client with a connection pool and a `Serializer`. Its implemented operations
are `set`, `get`, `get_with_ttl`, `delete`, `exists`, `clear`, and `__len__`.
`set` JSON-serializes before storage; `get` and `get_with_ttl` deserialize the
retrieved JSON. A missing remote value raises `KeyError`.

Pass these settings through `RedisConfig`:

| Option | Default | Meaning / when to change it |
| --- | --- | --- |
| `host` | `"localhost"` | Redis/Valkey hostname; change for a remote service. |
| `port` | `6379` | Server port. |
| `db` | `0` | Redis logical database; use a dedicated DB where appropriate. |
| `password` | `None` | Authentication password for a protected server. |
| `decode_responses` | `True` | Ask redis-py to decode responses to strings. |
| `max_connections` | `None` | Optional cap on connections in the pool. |
| `pool_timeout` | `None` | When set, wait this long for a pool connection. |

```python
from hydict import HDict, RedisConfig

cache = HDict(RedisConfig(
    host="cache.internal",
    port=6379,
    db=0,
    password="...",
    max_connections=20,
    pool_timeout=5,
))
```

## 10. Connection pooling and failures

```text
HDict -> RemoteBackend -> redis.Redis -> Connection Pool -> Redis / Valkey
```

With `pool_timeout=None`, `RemoteBackend` uses `redis.ConnectionPool`. With a
timeout, it uses `redis.BlockingConnectionPool`, which waits up to that timeout
for an available connection. `max_connections` bounds the pool when set. This
avoids establishing a new TCP connection for every remote operation and makes
concurrent access practical.

`RedisConnectionError` becomes `BackendConnectionError`; other `RedisError`
instances become `BackendOperationError`. These failures propagate from the
public `HDict` operation. A pool that cannot provide a connection is treated as
a connection failure by the backend. A remote failure does not roll back an L1
write that already happened.

## 11. Backend abstraction

`Backend` is an abstract base class with `set`, `get`, `get_with_ttl`,
`delete`, `exists`, `clear`, and `__len__`. `MemoryBackend` and
`RemoteBackend` implement this shared shape.

```text
HDict
  |
Backend interface
  |
  +-- MemoryBackend
  +-- RemoteBackend
```

The abstraction lets `HDict` coordinate cache layers without embedding Redis
details in its L1 implementation, and lets tests use in-memory/fake backends
to exercise behavior. A new backend must implement every abstract method,
including TTL-aware `get_with_ttl()`, and preserve the expected `KeyError` miss
behavior if it is to be used by `HDict`.

## 12. Serialization

Only L2 serialization is automatic:

```text
Python JSON-compatible value -> Serializer -> JSON text -> Redis
Redis value -> JSON text -> Serializer -> Python value
```

`Serializer.serialize()` calls `json.dumps()` and `deserialize()` calls
`json.loads()`. The tests cover strings, integers, floats, booleans, `None`,
lists, and dictionaries. Values must therefore be JSON-serializable; arbitrary
Python objects such as a typical custom class instance are not supported unless
the standard JSON encoder can encode them. L1 stores the original Python value
without serialization.

## 13. Exceptions

```text
HydictError
  |
  +-- BackendError
       +-- BackendConnectionError
       +-- BackendOperationError
```

- A missing cache key is `KeyError`.
- An unavailable Redis/Valkey backend is `BackendConnectionError`.
- Another Redis operation failure is `BackendOperationError`.

Translation gives callers stable package-level exceptions rather than exposing
redis-py exception classes throughout application code.

```python
from hydict import BackendConnectionError

try:
    value = cache["user:42"]
except KeyError:
    value = load_user_from_database(42)
except BackendConnectionError:
    # Apply the application's fallback policy.
    value = load_user_from_database(42)
```

## 14. Invalidation

`cache.invalidate(key)` delegates to `CacheInvalidator`. It attempts L1 delete
and then L2 delete, suppressing `KeyError` for either missing layer.

```text
Database changes -> cache.invalidate(key) -> next read misses -> application loads fresh data
```

Invalidation deletes cached data; it does not refresh it or load a replacement.
Use it after a source-of-truth update when the next request should obtain fresh
data.

## 15. Stampede protection and per-key locking

Without coordination, a popular missing key can cause many expensive loaders:

```text
100 requests -> miss -> DB, DB, DB, ...
```

`get_or_set()` changes the sequence to:

```text
lookup -> miss -> lock for this key -> lookup again -> one loader -> set -> return
```

The second lookup is critical: another thread may have filled the cache while
the current thread waited for its key lock. If that second lookup hits, the
loader is skipped. A loader exception propagates, and the `with lock` block
releases the lock so a later request can retry.

`StampedeProtection` keeps a dictionary of locks protected by a small global
lock. Different keys receive different locks, so work for `user:1` need not
block work for `user:2`. The current implementation never removes locks from
that dictionary; a process that sees an unbounded number of distinct keys can
therefore grow its lock dictionary over time. These locks are process-local,
not distributed across application instances.

## 16. Thread safety and consistency

`MemoryBackend` protects its individual operations with an `RLock`; tests cover
concurrent reads, writes, gets/deletes, and LRU capacity behavior. `get_or_set`
coordinates one loader per key inside one process.

This does **not** make the whole L1-plus-L2 operation atomic:

```text
L1 set
  |
  +-- L2 set
```

Another thread can observe a state between those calls, and separate processes
do not share the in-process stampede locks. Applications requiring distributed
single-flight or transactional cache/database updates need an additional
coordination mechanism.

## 17. Metrics and observability

`MetricsCollector` increments counters for each `HDict` instance. `l1_hits`
counts direct L1 reads; `l2_hits` counts remote reads that are promoted to L1;
`total_hits` is their sum. `misses` counts unsuccessful public lookups.
`loader_calls` deliberately means loader calls rather than database calls: a
loader can perform any work.

```python
cache = HDict(max_entries=1)
cache.get_or_set("user:42", lambda: fetch_user_from_database(42))
print(cache.stats())
# first request: one miss and one loader call

cache["user:42"]
print(cache.stats())
# second request: L1 hit increases
```

After L1 eviction, an L2-backed read increments `l2_hits` and repopulates L1.
The metrics collector itself has no locking, so its counters should be treated
as observability signals rather than an atomic accounting system under heavy
concurrency.

## 18. Failure behavior

| Situation | Current behavior |
| --- | --- |
| Key absent from all enabled layers | `KeyError`, or `get()` returns its default. |
| Redis unavailable / pool cannot connect | `BackendConnectionError`. |
| Other Redis failure | `BackendOperationError`. |
| Loader raises | Exception propagates; its key lock is released. |
| TTL expires | Entry is removed lazily and behaves as a miss. |
| L1 evicts a key | L1 loses it; L2 retains it if configured. |
| L2 has value, L1 does not | Value is promoted to L1 and returned. |

## 19. Testing strategy

The suite is organized around memory/backend behavior, core mapping and remote
flows, serialization, invalidation, metrics, LRU eviction, concurrency, and
stampede protection. Tests that use a live Redis connection are opt-in locally
through `HYDICT_REDIS_INTEGRATION=1`; the GitHub Actions Redis job enables them
and runs the complete `pytest -q` suite against Redis 7.

The V5 release verification recorded 82 passing tests. Locally, the Redis tests
are skipped unless a Redis/Valkey server is available and the environment flag
is enabled.

```powershell
python -m pip install -e .
pytest -q

# With a Redis-compatible server running locally:
$env:HYDICT_REDIS_INTEGRATION = "1"
pytest -q
```

## 20. Complete usage patterns

### L1 only

```python
cache = HDict(max_entries=500)
cache.set("profile:42", {"name": "Veeresh"}, ttl=300)
```

### Redis or Valkey L2

```python
config = RedisConfig(host="localhost", db=0, max_connections=10)
cache = HDict(config=config, max_entries=500)
```

### Invalidation, loading, and metrics

```python
cache.invalidate("profile:42")

profile = cache.get_or_set(
    "profile:42",
    lambda: fetch_profile(42),
    ttl=300,
)

print(cache.stats())
```

## 21. Performance considerations

Performance comes from serving hot values from memory, avoiding remote calls on
L1 hits, restoring an evicted L1 value from L2, bounding memory with LRU, and
reusing remote connections. Per-key locking avoids duplicate work on a common
miss. L2 lookups and writes still incur serialization and network latency; L1
promotion is an optimization, not a removal of remote latency on the first L2
hit.

## 22. Current limitations and future work

- The exposed API is synchronous. `src/hydict/async_api` currently contains no
  async cache implementation.
- Per-key locks are local to one process and are retained for its lifetime.
- L1 and L2 writes/invalidation are not distributed transactions.
- L2 storage requires Redis/Valkey availability and JSON-compatible values.
- Metrics are per-instance counters, not a distributed or atomic metrics
  system.

### Planned / Future Work: V6

V6 is planned to add an `asyncio`-oriented API and asynchronous Redis
operations. No async `HDict` API is implemented in V5, so application code
should use the synchronous API documented above.

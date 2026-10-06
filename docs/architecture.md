# Architecture

## Cache layers

`HDict` is a synchronous, two-level mapping:

1. `MemoryBackend` provides the local L1 cache.
2. `RemoteBackend` optionally provides Redis/Valkey-backed L2 storage.

When no `RedisConfig` is supplied, `HDict` uses L1 only. When a remote backend
is configured, writes are sent to L1 and L2. Reads prefer L1; on an L1 miss,
`HDict` checks L2 and promotes an L2 hit into L1.

```text
read(key)
   |
   +-- L1 hit --> return value
   |
   +-- L1 miss --> L2 hit --> promote to L1 --> return value
                  |
                  +-- L2 miss --> KeyError (or a get_or_set loader)
```

## Expiration and eviction

Both cache layers can receive a TTL through `HDict.set()` or
`HDict.get_or_set()`. When a value is promoted from L2, the remaining TTL is
applied to L1. L1 uses an ordered mapping and evicts the least recently used
item when `max_entries` is exceeded.

## Concurrency

The L1 backend protects its internal state with a re-entrant lock. Individual
public operations are safe to call concurrently, but operations across L1 and
L2 are not a single atomic transaction.

`get_or_set()` first checks the cache, then obtains a lock for that key and
checks again before calling its loader. This prevents concurrent misses for the
same key from causing multiple loader calls. A loader exception is propagated;
the lock is released when the call exits.

## Operations and observability

- `invalidate(key)` removes a key from L1 and, when present, L2.
- `stats()` reports L1 hits, L2 hits, total hits, misses, and loader calls.
- Redis/Valkey backend errors are exposed as the package's backend error types.

The public API is exposed through `hydict.HDict` and `hydict.RedisConfig`.
Implementation modules remain under their respective subpackages.

## Testing

Redis integration tests are opt-in so unit tests do not require a running Redis
server. Set `HYDICT_REDIS_INTEGRATION=1` before running the integration test.

## Planned work

The 0.5.0 release exposes a synchronous API. An asynchronous API is planned for
0.6.0 and is not available in this release.

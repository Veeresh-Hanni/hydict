# Release history

All notable changes to `hydict` are documented here.

## Version 0.5.0

### Added

- Hierarchical caching with local L1 memory and optional Redis/Valkey L2 storage.
- L2-to-L1 promotion on remote cache hits.
- TTL support, including TTL preservation while promoting a value from L2 to L1.
- LRU eviction with configurable in-memory capacity through `max_entries`.
- Redis connection pooling configuration.
- Cache invalidation across configured cache layers.
- Cache statistics via `HDict.stats()`.
- `HDict.get_or_set()` for loading and caching a missing value.
- Per-key locking to reduce concurrent loader calls for the same missing key.
- GitHub Actions checks for unit tests and a complete Redis-backed `pytest -q`
  test suite.
- A tag-triggered PyPI publishing workflow that runs only after both test jobs
  succeed.

### Verified

- V5 release verification recorded 82 passing tests.
- A cached value bypasses the `get_or_set()` loader.
- An L2 hit is used before invoking a `get_or_set()` loader.
- A loader exception releases its per-key lock so a later attempt can retry.

### Planned

- `0.6.0` (V6): an asynchronous API for `asyncio` applications.

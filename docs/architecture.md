# Architecture

`HDict` is a two-level mapping:

1. `MemoryBackend` provides the local L1 cache.
2. `RemoteBackend` optionally provides Redis/Valkey-backed L2 storage.

Writes go to both configured levels. Reads use memory first and promote an L2
value into memory. The package keeps the public `hydict.HDict`,
`hydict.backends`, and `hydict.config` imports small while implementation
modules live in their respective subpackages.

Redis integration tests are opt-in so unit tests do not require a running
Redis server. Set `HYDICT_REDIS_INTEGRATION=1` before running the integration
test.

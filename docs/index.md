# hydict

`hydict` is a dict-compatible, hierarchical cache for Python. It combines an
in-process L1 memory cache with optional Redis or Valkey L2 storage.

## Start here

```bash
pip install hydict
```

```python
from hydict import HDict

cache = HDict()
cache["name"] = "Veeresh"
print(cache["name"])
```

## Documentation

- [Architecture](architecture.md) explains the L1/L2 design and current
  consistency model.
- [Developer guide](developer-guide.md) documents the V5 API, configuration,
  error behavior, testing approach, and limitations.
- [Release history](changelog.md) records version changes.

## Scope

The V5 API is synchronous. An asynchronous API is planned for V6 and is not
available in the current release.

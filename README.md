 # hydict

An in-memory dictionary with an optional Redis/Valkey remote backend.

```python
from hydict import HDict
from hydict.config import CacheConfig

cache = HDict(CacheConfig())
cache["name"] = "Veeresh"
assert cache["name"] == "Veeresh"
```

See [docs/architecture.md](docs/architecture.md) for the package layout and
cache behavior.
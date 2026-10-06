from ..stampede.protection import StampedeProtection

from ..backends.memory import MemoryBackend
from ..backends.remote import RemoteBackend
from ..config.redis import RedisConfig
from ..invalidation import CacheInvalidator
from ..metrics import MetricsCollector

class HDict:
    """
    Thread-safe hybrid cache.

    Thread-safety guarantees:
    - Individual public operations are safe to call concurrently.
    - The in-memory L1 backend protects its internal state with a lock.
    - L1 and L2 operations are not an atomic transaction.
    - A thread may observe another thread's update between L1 and L2 operations.
    """
    def __init__(self, config=None, max_entries=None):
        self._memory = MemoryBackend(max_entries=max_entries)

        self._remote = None

        if config is not None:
            self._remote = RemoteBackend(config)
            
        self._invalidator = CacheInvalidator(
                                    self._memory,
                                    self._remote,
                                )
        self._stampede = StampedeProtection()
        self._metrics = MetricsCollector()

    def __setitem__(self, key, value):
        # Write to L1
        self._memory.set(key, value)

        # Write to L2
        if self._remote is not None:
            self._remote.set(key, value)

    def __getitem__(self, key, _record_metrics=True):
        if self._memory.exists(key):
            if _record_metrics:
                self._metrics.record_l1_hit()
            return self._memory.get(key)

        if self._remote is not None:
            try:
                value, ttl = self._remote.get_with_ttl(key)
            except KeyError:
                if _record_metrics:
                    self._metrics.record_miss()
                raise

            if _record_metrics:
                self._metrics.record_l2_hit()

            if ttl < 0:
                self._memory.set(key, value)
            else:
                self._memory.set(key, value, ttl=ttl)

            return value

        if _record_metrics:
            self._metrics.record_miss()

        raise KeyError(key)
    
    def __delitem__(self, key):
        self._memory.delete(key)

        if self._remote is not None:
            self._remote.delete(key)

    def __contains__(self, key):

        if self._memory.exists(key):
            return True

        if self._remote is not None:
            return self._remote.exists(key)

        return False

    def __len__(self):
        return len(self._memory)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def clear(self):
        self._memory.clear()

        if self._remote is not None:
            self._remote.clear()

    def set(self, key, value, ttl=None):
        self._memory.set(key, value, ttl=ttl)

        if self._remote is not None:
            self._remote.set(key, value, ttl=ttl)

    def invalidate(self, key):
        self._invalidator.invalidate(key)

    def get_or_set(self, key, loader, ttl=None):
        try:
            return self[key]
        except KeyError:
            pass

        lock = self._stampede.get_lock(key)

        with lock:
            try:
                return self.__getitem__(key, _record_metrics=False)
            except KeyError:
                pass

            self._metrics.record_loader_call()

            value = loader()
            self.set(key, value, ttl=ttl)

            return value

    def stats(self):
        return {
            "l1_hits": self._metrics.l1_hits,
            "l2_hits": self._metrics.l2_hits,
            "total_hits": self._metrics.l1_hits + self._metrics.l2_hits,
            "misses": self._metrics.misses,
            "loader_calls": self._metrics.loader_calls,
        }
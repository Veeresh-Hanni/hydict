from collections import OrderedDict
import threading
import time

from .base import Backend

class MemoryBackend(Backend):

    def __init__(self, max_entries=None):
        self._data = OrderedDict()
        self._expiry = {}
        self.max_entries = max_entries
        self._lock = threading.RLock()

    def set(self, key, value, ttl=None):
        with self._lock:
            self._data[key] = value
            self._data.move_to_end(key)

            if ttl is None:
                self._expiry.pop(key, None)
            else:
                self._expiry[key] = time.monotonic() + ttl

            self._evict_if_needed()

    def get(self, key):
        with self._lock:
            self._remove_if_expired(key)

            value = self._data[key]

            self._data.move_to_end(key)

            return value

    def get_with_ttl(self, key):
        with self._lock:
            self._remove_if_expired(key)

            if key not in self._data:
                raise KeyError(key)

            expiry = self._expiry.get(key)

            if expiry is None:
                ttl = -1
            else:
                remaining = expiry - time.monotonic()

                if remaining <= 0:
                    self._remove_if_expired(key)
                    raise KeyError(key)

                ttl = max(0, int(remaining))

            self._data.move_to_end(key)

            return self._data[key], ttl

    def delete(self, key):
        with self._lock:
            self._remove_if_expired(key)

            del self._data[key]
            self._expiry.pop(key, None)

    def exists(self, key):
        with self._lock:
            self._remove_if_expired(key)
            return key in self._data

    def clear(self):
        with self._lock:
            self._data.clear()
            self._expiry.clear()

    def __len__(self):
        with self._lock:
            self._remove_expired()
            return len(self._data)

    def _evict_if_needed(self):
        if self.max_entries is None:
            return

        while len(self._data) > self.max_entries:
            oldest_key, _ = self._data.popitem(last=False)
            self._expiry.pop(oldest_key, None)

    def _remove_if_expired(self, key):
        expiry = self._expiry.get(key)

        if expiry is not None and time.monotonic() >= expiry:
            self._data.pop(key, None)
            self._expiry.pop(key, None)

    def _remove_expired(self):
        for key in list(self._expiry):
            self._remove_if_expired(key)

    
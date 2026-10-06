import threading

class StampedeProtection:

    def __init__(self):
        self._locks = {}
        self._lock = threading.Lock()

    def get_lock(self, key):
        with self._lock:
            if key not in self._locks:
                self._locks[key] = threading.Lock()

            return self._locks[key]


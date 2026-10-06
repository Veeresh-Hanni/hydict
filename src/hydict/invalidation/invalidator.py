from hydict.backends import Backend


class CacheInvalidator:

    def __init__(self, l1: Backend, l2: Backend | None = None):
        self.l1 = l1
        self.l2 = l2

    def invalidate(self, key):
        """
        Remove a key from both L1 and L2.

        Missing keys are ignored.
        """
        self._delete(self.l1, key)
        if self.l2 is not None:
            self._delete(self.l2, key)

    @staticmethod
    def _delete(backend: Backend, key):
        try:
            backend.delete(key)
        except KeyError:
            pass
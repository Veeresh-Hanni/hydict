from abc import ABC, abstractmethod


class Backend(ABC):

    @abstractmethod
    def set(self, key, value, ttl=None):
        pass

    @abstractmethod
    def get(self, key):
        pass

    @abstractmethod
    def get_with_ttl(self, key):
        pass

    @abstractmethod
    def delete(self, key):
        pass

    @abstractmethod
    def exists(self, key):
        pass

    @abstractmethod
    def clear(self):
        pass

    @abstractmethod
    def __len__(self):
        pass
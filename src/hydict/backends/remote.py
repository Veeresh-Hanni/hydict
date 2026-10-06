import redis

from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError

from ..config.redis import RedisConfig
from .base import Backend

from ..exceptions import (
    BackendConnectionError,
    BackendOperationError,
)

from ..serialization import Serializer

class RemoteBackend(Backend):
    
    def __init__(self, config: RedisConfig):
        if config.pool_timeout is None:
            pool = redis.ConnectionPool(
                host=config.host,
                port=config.port,
                db=config.db,
                password=config.password,
                decode_responses=config.decode_responses,
                max_connections=config.max_connections,
            )
        else:
            pool = redis.BlockingConnectionPool(
                host=config.host,
                port=config.port,
                db=config.db,
                password=config.password,
                decode_responses=config.decode_responses,
                max_connections=config.max_connections,
                timeout=config.pool_timeout,
            )

        self.client = redis.Redis(connection_pool=pool)
        self.serializer = Serializer()

    def set(self, key, value, ttl=None):
        try:
            value = self.serializer.serialize(value)

            if ttl is None:
                self.client.set(key, value)
            else:
                self.client.set(key, value, ex=ttl)

        except RedisConnectionError as exc:
            raise BackendConnectionError(
                "Remote backend connection failed"
            ) from exc

        except RedisError as exc:
            raise BackendOperationError(
                f"Failed to set key: {key}"
            ) from exc

    def get(self, key):
        try:
            value = self.client.get(key)

        except RedisConnectionError as exc:
            raise BackendConnectionError(
                "Remote backend connection failed"
            ) from exc

        except RedisError as exc:
            raise BackendOperationError(
                f"Failed to get key: {key}"
            ) from exc

        if value is None:
            raise KeyError(key)

        return self.serializer.deserialize(value)

    def delete(self, key):
        try:
            self.client.delete(key)

        except RedisConnectionError as exc:
            raise BackendConnectionError(
                "Remote backend connection failed"
            ) from exc

        except RedisError as exc:
            raise BackendOperationError(
                f"Failed to delete key: {key}"
            ) from exc

    def exists(self, key):
        try:
            return self.client.exists(key) > 0

        except RedisConnectionError as exc:
            raise BackendConnectionError(
                "Remote backend connection failed"
            ) from exc

        except RedisError as exc:
            raise BackendOperationError(
                f"Failed to check key: {key}"
            ) from exc

    def clear(self):
        try:
            self.client.flushdb()

        except RedisConnectionError as exc:
            raise BackendConnectionError(
                "Remote backend connection failed"
            ) from exc

        except RedisError as exc:
            raise BackendOperationError(
                "Failed to clear remote backend"
            ) from exc

    def get_with_ttl(self, key):
        try:
            value = self.client.get(key)

            if value is None:
                raise KeyError(key)

            ttl = self.client.ttl(key)

            return self.serializer.deserialize(value), ttl

        except RedisConnectionError as exc:
            raise BackendConnectionError(
                "Remote backend connection failed"
            ) from exc

        except RedisError as exc:
            raise BackendOperationError(
                f"Failed to get key: {key}"
            ) from exc

    def __len__(self):
        try:
            return self.client.dbsize()
        except RedisConnectionError as exc:
            raise BackendConnectionError(
                "Remote backend connection failed"
            ) from exc
        except RedisError as exc:
            raise BackendOperationError(
                "Failed to get remote backend size"
            ) from exc
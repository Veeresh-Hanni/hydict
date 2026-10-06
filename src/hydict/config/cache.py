from dataclasses import dataclass


@dataclass
class CacheConfig:
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str | None = None
    decode_responses: bool = True
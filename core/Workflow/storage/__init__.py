"""
Data storage and persistence modules.

This package provides Redis-backed storage services following
the Single Responsibility Principle:

- RedisConnection: Connection lifecycle management
- QueueStore: Queue operations (push/pop/length)
- CacheStore: Cache operations (set/get/delete/exists)
- DataStore: Facade providing unified access to all services
- utils: Shared serialization utilities
"""

from .redis_connection import RedisConnection
from .queue_store import QueueStore
from .cache_store import CacheStore
from .data_store import DataStore
from .utils import serialize, deserialize

__all__ = [
    "RedisConnection",
    "QueueStore",
    "CacheStore",
    "DataStore",
    "serialize",
    "deserialize",
]

"""
DataStore - Facade for Storage Services

This module provides a unified interface to storage services following the
Single Responsibility Principle. The DataStore class acts as a facade,
delegating actual operations to specialized classes:

- RedisConnection: Connection lifecycle management
- QueueStore: Queue operations (push/pop/length)
- CacheStore: Cache operations (set/get/delete/exists)

Usage:
    data_store = DataStore()
    await data_store.queue.push("my_queue", {"key": "value"})
    await data_store.cache.set("my_key", {"data": 123})
"""

import structlog
from typing import Optional

from .redis_connection import RedisConnection
from .queue_store import QueueStore
from .cache_store import CacheStore

logger = structlog.get_logger(__name__)


class DataStore:
    """
    Facade providing unified access to storage services.
    
    This class follows the Facade pattern, providing a simple interface
    to the underlying storage subsystems.
    
    Architecture (SRP-compliant):
    - RedisConnection: Handles connection lifecycle only
    - QueueStore: Handles queue operations only
    - CacheStore: Handles cache operations only
    - DataStore: Coordinates access to all services (Facade)
    
    Usage:
        data_store = DataStore()
        
        # Queue operations
        await data_store.queue.push("my_queue", {"key": "value"})
        item = await data_store.queue.pop("my_queue")
        length = await data_store.queue.length("my_queue")
        
        # Cache operations
        await data_store.cache.set("my_key", {"data": 123}, ttl=3600)
        value = await data_store.cache.get("my_key")
        await data_store.cache.delete("my_key")
        exists = await data_store.cache.exists("my_key")
    """
    
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        pool_size: int = 10
    ):
        """
        Initialize DataStore with Redis connection parameters.
        
        Args:
            host: Redis host address
            port: Redis port
            db: Redis database number
            password: Optional Redis password
            pool_size: Connection pool size (reserved for future use)
        """
        # Prevent re-initialization if already initialized
        if hasattr(self, '_initialized'):
            return
        
        # Initialize the shared connection manager
        self._redis_connection = RedisConnection(
            host=host,
            port=port,
            db=db,
            password=password
        )
        
        # Initialize specialized stores with shared connection
        self._queue_store = QueueStore(self._redis_connection)
        self._cache_store = CacheStore(self._redis_connection)
        
        self._initialized = True
        logger.info(
            "DataStore initialized",
            host=host,
            port=port,
            db=db
        )
    
    @property
    def queue(self) -> QueueStore:
        """
        Access queue operations.
        
        Returns:
            QueueStore: Queue service for push/pop/length operations
            
        Example:
            await data_store.queue.push("my_queue", {"data": "value"})
            item = await data_store.queue.pop("my_queue")
            length = await data_store.queue.length("my_queue")
        """
        return self._queue_store
    
    @property
    def cache(self) -> CacheStore:
        """
        Access cache operations.
        
        Returns:
            CacheStore: Cache service for set/get/delete/exists operations
            
        Example:
            await data_store.cache.set("my_key", {"data": "value"}, ttl=3600)
            value = await data_store.cache.get("my_key")
            await data_store.cache.delete("my_key")
            exists = await data_store.cache.exists("my_key")
        """
        return self._cache_store
    
    @property
    def connection(self) -> RedisConnection:
        """
        Access the underlying Redis connection manager.
        
        Returns:
            RedisConnection: Connection manager for advanced use cases
        """
        return self._redis_connection
    
    async def close(self):
        """
        Close the Redis connection.
        Should be called when the DataStore is no longer needed.
        """
        await self._redis_connection.close()

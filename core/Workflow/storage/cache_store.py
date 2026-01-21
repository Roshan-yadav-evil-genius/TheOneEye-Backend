"""
Cache Store

Single Responsibility: Cache operations using Redis Strings.
This class handles only cache-related operations (set, get, delete, exists).
"""

import structlog
from typing import Any, Optional

from .redis_connection import RedisConnection
from .utils import serialize, deserialize

logger = structlog.get_logger(__name__)


class CacheStore:
    """
    Handles cache operations using Redis Strings.
    
    Single Responsibility: Cache operations only.
    - Set cache values with optional TTL
    - Get cached values
    - Delete cache entries
    - Check cache key existence
    
    This class does NOT handle connection management or queue operations.
    """
    
    def __init__(self, connection: RedisConnection, prefix: str = "datastore:"):
        """
        Initialize CacheStore with a Redis connection.
        
        Args:
            connection: RedisConnection instance for Redis operations
            prefix: Key prefix for cache keys (default: "datastore:")
        """
        self._connection = connection
        self._prefix = prefix
    
    def _cache_key(self, key: str) -> str:
        """Get Redis key for cache."""
        return f"{self._prefix}cache:{key}"
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set a value in the cache.
        
        This operation is process-safe - multiple processes can write to
        the same key, with the last write winning.
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Optional time-to-live in seconds
            
        Raises:
            Exception: If set operation fails
        """
        conn = await self._connection.ensure_connection()
        cache_key = self._cache_key(key)
        serialized_value = serialize(value)
        
        try:
            if ttl is not None:
                await conn.setex(cache_key, ttl, serialized_value)
            else:
                await conn.set(cache_key, serialized_value)
            logger.debug(f"Set cache key '{key}'")
        except Exception as e:
            logger.error(
                f"Failed to set cache key '{key}': {e}",
                exc_info=True
            )
            raise
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        This operation is process-safe - multiple processes can read from
        the same key simultaneously.
        
        Args:
            key: Cache key
            
        Returns:
            Any: Cached value (deserialized), or None if not found
            
        Raises:
            Exception: If get operation fails
        """
        conn = await self._connection.ensure_connection()
        cache_key = self._cache_key(key)
        
        try:
            serialized_value = await conn.get(cache_key)
            if serialized_value is None:
                return None
            return deserialize(serialized_value)
        except Exception as e:
            logger.error(
                f"Failed to get cache key '{key}': {e}",
                exc_info=True
            )
            raise
    
    async def delete(self, key: str):
        """
        Delete a value from the cache.
        
        Args:
            key: Cache key to delete
            
        Raises:
            Exception: If delete operation fails
        """
        conn = await self._connection.ensure_connection()
        cache_key = self._cache_key(key)
        
        try:
            await conn.delete([cache_key])
            logger.debug(f"Deleted cache key '{key}'")
        except Exception as e:
            logger.error(
                f"Failed to delete cache key '{key}': {e}",
                exc_info=True
            )
            raise
    
    async def exists(self, key: str) -> bool:
        """
        Check if a cache key exists.
        
        Args:
            key: Cache key to check
            
        Returns:
            bool: True if key exists, False otherwise
            
        Raises:
            Exception: If exists check fails
        """
        conn = await self._connection.ensure_connection()
        cache_key = self._cache_key(key)
        
        try:
            exists = await conn.exists(cache_key)
            return bool(exists)
        except Exception as e:
            logger.error(
                f"Failed to check existence of cache key '{key}': {e}",
                exc_info=True
            )
            raise


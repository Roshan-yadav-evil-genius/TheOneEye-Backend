"""
Redis Connection Manager

Single Responsibility: Manages Redis connection lifecycle.
This class handles only connection establishment, maintenance, and closure.
"""

import structlog
from typing import Optional
import asyncio_redis

logger = structlog.get_logger(__name__)


class RedisConnection:
    """
    Manages Redis connection lifecycle.
    
    Single Responsibility: Connection management only.
    - Establishes connection lazily on first use
    - Maintains connection state
    - Handles connection closure
    
    This class does NOT handle any data operations (queues, cache, etc.)
    """
    
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None
    ):
        """
        Initialize connection parameters.
        
        Args:
            host: Redis host address
            port: Redis port
            db: Redis database number
            password: Optional Redis password
        """
        self._host = host
        self._port = port
        self._db = db
        self._password = password
        self._connection: Optional[asyncio_redis.Connection] = None
    
    @property
    def connection(self) -> Optional[asyncio_redis.Connection]:
        """Get the current connection instance."""
        return self._connection
    
    @property
    def is_connected(self) -> bool:
        """Check if connection is established."""
        return self._connection is not None
    
    async def ensure_connection(self) -> asyncio_redis.Connection:
        """
        Ensure Redis connection is established.
        Creates connection lazily on first use.
        
        Returns:
            asyncio_redis.Connection: The active Redis connection
            
        Raises:
            Exception: If connection fails
        """
        if self._connection is None:
            try:
                self._connection = await asyncio_redis.Connection.create(
                    host=self._host,
                    port=self._port,
                    db=self._db,
                    password=self._password
                )
                logger.info(
                    "Connected to Redis",
                    host=self._host,
                    port=self._port,
                    db=self._db
                )
            except Exception as e:
                logger.error(
                    "Failed to connect to Redis",
                    host=self._host,
                    port=self._port,
                    error=str(e),
                    exc_info=True
                )
                raise
        return self._connection
    
    async def close(self):
        """
        Close the Redis connection.
        Safe to call even if not connected.
        """
        if self._connection is not None:
            self._connection.close()
            self._connection = None
            logger.info("Redis connection closed")
    
    async def reconnect(self):
        """
        Force reconnection to Redis.
        Closes existing connection and establishes a new one.
        """
        await self.close()
        await self.ensure_connection()


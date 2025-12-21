"""
Queue Store

Single Responsibility: Queue operations using Redis Lists.
This class handles only queue-related operations (push, pop, length).
"""

import structlog
from typing import Any, Dict, Optional

from .redis_connection import RedisConnection
from .utils import serialize, deserialize

logger = structlog.get_logger(__name__)


class QueueStore:
    """
    Handles queue operations using Redis Lists.
    
    Single Responsibility: Queue operations only.
    - Push data to queues (LPUSH)
    - Pop data from queues (BRPOP)
    - Get queue length (LLEN)
    
    This class does NOT handle connection management or cache operations.
    """
    
    def __init__(self, connection: RedisConnection, prefix: str = "datastore:"):
        """
        Initialize QueueStore with a Redis connection.
        
        Args:
            connection: RedisConnection instance for Redis operations
            prefix: Key prefix for queue names (default: "datastore:")
        """
        self._connection = connection
        self._prefix = prefix
    
    def _queue_key(self, queue_name: str) -> str:
        """Get Redis key for a queue."""
        return f"{self._prefix}queue:{queue_name}"
    
    async def push(self, queue_name: str, data: Dict):
        """
        Push data to a named queue using Redis LPUSH.
        
        This operation is process-safe - multiple processes can push to
        the same queue simultaneously without issues.
        
        Args:
            queue_name: Name of the queue
            data: Data to push to the queue (will be JSON serialized)
            
        Raises:
            Exception: If push operation fails
        """
        conn = await self._connection.ensure_connection()
        queue_key = self._queue_key(queue_name)
        serialized_data = serialize(data)
        
        try:
            logger.info("Pushing data to queue", queue_key=queue_key)
            await conn.lpush(queue_key, [serialized_data])
            logger.info("Pushed to queue", queue_key=queue_key)
        except Exception as e:
            logger.error(
                f"Failed to push to queue '{queue_name}': {e}",
                exc_info=True
            )
            raise
    
    async def pop(self, queue_name: str, timeout: Optional[float] = None) -> Optional[Any]:
        """
        Pop data from a named queue using Redis BRPOP (blocking right pop).
        
        This operation is process-safe - multiple processes can pop from
        the same queue, and Redis will ensure each message is delivered
        to only one consumer.
        
        Args:
            queue_name: Name of the queue
            timeout: Optional timeout in seconds for blocking pop operation.
                    If None, blocks indefinitely. If 0, returns immediately.
            
        Returns:
            Any: Data popped from the queue (deserialized), or None if timeout occurs
            
        Raises:
            Exception: If pop operation fails
        """
        conn = await self._connection.ensure_connection()
        queue_key = self._queue_key(queue_name)
        logger.info("Popping from queue", queue_key=queue_key)
        
        try:
            # Convert timeout to integer seconds for Redis BRPOP
            # BRPOP timeout of 0 means return immediately, None means block indefinitely
            if timeout is None:
                # Block indefinitely - don't pass timeout parameter
                result = await conn.brpop([queue_key])
            elif timeout == 0:
                # Return immediately
                result = await conn.brpop([queue_key], timeout=0)
            else:
                # Block for specified seconds
                redis_timeout = int(timeout)
                result = await conn.brpop([queue_key], timeout=redis_timeout)
            
            if result is None:
                return None
            
            # BRPOP returns BlockingPopReply object with value attribute
            serialized_data = result.value
            data = deserialize(serialized_data)
            logger.info("Popped from queue", queue_key=queue_key)
            return data
            
        except Exception as e:
            logger.error(
                f"Failed to pop from queue '{queue_name}': {e}",
                exc_info=True
            )
            raise
    
    async def length(self, queue_name: str) -> int:
        """
        Get the length of a queue.
        
        Args:
            queue_name: Name of the queue
            
        Returns:
            int: Number of items in the queue
            
        Raises:
            Exception: If length operation fails
        """
        conn = await self._connection.ensure_connection()
        queue_key = self._queue_key(queue_name)
        
        try:
            length = await conn.llen(queue_key)
            return length
        except Exception as e:
            logger.error(
                f"Failed to get queue length for '{queue_name}': {e}",
                exc_info=True
            )
            raise


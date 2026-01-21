"""
Webhook Pub/Sub Store

Single Responsibility: Redis pub/sub operations for webhook data.
This class handles only pub/sub operations (publish, subscribe).
"""

import json
import structlog
from typing import Any, Dict, Optional
import redis
from asyncio_redis import Connection

logger = structlog.get_logger(__name__)


class WebhookPubSubStore:
    """
    Handles webhook pub/sub operations using Redis pub/sub.
    
    Single Responsibility: Webhook pub/sub operations only.
    - Publish data to webhook channels
    - Subscribe to webhook channels and wait for messages (blocks indefinitely)
    
    Architecture:
    - Uses sync Redis client for publishing (from HTTP endpoint)
    - Uses async Redis connection for subscribing (in nodes)
    - Channel format: webhook:{webhook_id}
    - Publish-and-forget: If no subscribers, message is lost
    """
    
    CHANNEL_PREFIX = "webhook:"
    
    def __init__(self):
        """Initialize with sync Redis client for publishing."""
        self._redis_client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True
        )
    
    def _get_channel(self, webhook_id: str) -> str:
        """Get Redis channel name for webhook_id."""
        return f"{self.CHANNEL_PREFIX}{webhook_id}"
    
    def publish(self, webhook_id: str, data: Dict[str, Any]) -> int:
        """
        Publish data to a webhook channel.
        
        This is publish-and-forget: if no subscribers are listening,
        the message is lost (Redis pub/sub behavior).
        
        Args:
            webhook_id: The webhook identifier
            data: Data to publish (will be JSON serialized)
            
        Returns:
            int: Number of subscribers that received the message (0 if none)
            
        Raises:
            Exception: If publish operation fails
        """
        channel = self._get_channel(webhook_id)
        message = json.dumps(data)
        
        try:
            subscribers = self._redis_client.publish(channel, message)
            logger.info(
                "Published webhook data",
                webhook_id=webhook_id,
                channel=channel,
                subscribers=subscribers
            )
            return subscribers
        except Exception as e:
            logger.error(
                "Failed to publish webhook data",
                webhook_id=webhook_id,
                channel=channel,
                error=str(e),
                exc_info=True
            )
            raise
    
    async def subscribe(
        self, 
        webhook_id: str, 
        connection: Optional[Connection] = None
    ) -> Dict[str, Any]:
        """
        Subscribe to a webhook channel and wait for a message.
        
        This operation blocks indefinitely until a message is received.
        Uses a separate Redis connection for subscription (required for pub/sub).
        
        Args:
            webhook_id: The webhook identifier to subscribe to
            connection: Optional async Redis connection (creates new if None)
            
        Returns:
            Dict: Received webhook data (deserialized)
            
        Raises:
            Exception: If subscription fails
        """
        channel = self._get_channel(webhook_id)
        
        # Create a separate connection for subscription (required for pub/sub)
        created_connection = False
        if connection is None:
            connection = await Connection.create(
                host='localhost',
                port=6379,
                db=0
            )
            created_connection = True
        
        try:
            # Create subscriber
            subscriber = await connection.start_subscribe()
            await subscriber.subscribe([channel])
            
            logger.info(
                "Subscribed to webhook channel",
                webhook_id=webhook_id,
                channel=channel
            )
            
            # Wait for message (blocks indefinitely)
            message = await subscriber.next_published()
            
            # Deserialize message
            data = json.loads(message.value)
            
            logger.info(
                "Received webhook data",
                webhook_id=webhook_id,
                channel=channel
            )
            
            return data
            
        except Exception as e:
            logger.error(
                "Failed to subscribe to webhook channel",
                webhook_id=webhook_id,
                channel=channel,
                error=str(e),
                exc_info=True
            )
            raise
        finally:
            # Close subscription connection if we created it
            if created_connection and connection is not None:
                connection.close()


# Global singleton instance
webhook_pubsub_store = WebhookPubSubStore()

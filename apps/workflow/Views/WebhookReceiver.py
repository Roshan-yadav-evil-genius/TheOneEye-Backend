"""
Webhook Receiver View

Single Responsibility: Receive HTTP webhook requests and publish to Redis.
"""

import json
import structlog
import sys
from pathlib import Path
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

# Add core to path for imports
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
CORE_PATH = BASE_DIR / 'core'
if str(CORE_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_PATH))

from Workflow.storage.webhook_pubsub_store import webhook_pubsub_store

logger = structlog.get_logger(__name__)


class WebhookReceiverView(APIView):
    """
    Receives webhook POST requests and publishes to Redis pub/sub.
    
    Endpoint: POST /api/webhooks/{webhook_id}
    Body: JSON data to broadcast
    
    Returns: 202 Accepted (publish-and-forget)
    """
    
    authentication_classes = []  # Public endpoint
    permission_classes = []      # No authentication required
    
    def post(self, request, webhook_id: str):
        """
        Receive webhook data and publish to subscribers.
        
        Args:
            request: Django request object
            webhook_id: Webhook identifier from URL path
            
        Returns:
            Response with 202 Accepted status
        """
        try:
            # Parse JSON body
            try:
                body_data = json.loads(request.body) if request.body else {}
            except json.JSONDecodeError:
                body_data = {}
            
            # Prepare data to publish
            webhook_data = {
                'body': body_data,
                'headers': dict(request.headers),
                'method': request.method,
                'query_params': dict(request.GET),
            }
            
            # Publish to Redis channel
            subscribers = webhook_pubsub_store.publish(webhook_id, webhook_data)
            
            logger.info(
                "Webhook received and published",
                webhook_id=webhook_id,
                subscribers=subscribers,
                has_body=bool(body_data)
            )
            
            # Return 202 Accepted (publish-and-forget)
            message = 'Webhook data published' if subscribers > 0 else 'No subscribers listening'
            return Response(
                {
                    'status': 'accepted',
                    'webhook_id': webhook_id,
                    'subscribers': subscribers,
                    'message': message
                },
                status=status.HTTP_202_ACCEPTED
            )
            
        except Exception as e:
            logger.error(
                "Error processing webhook",
                webhook_id=webhook_id,
                error=str(e),
                exc_info=True
            )
            # Still return 202 to prevent retries from external systems
            return Response(
                {
                    'status': 'error',
                    'webhook_id': webhook_id,
                    'message': 'Error processing webhook'
                },
                status=status.HTTP_202_ACCEPTED
            )

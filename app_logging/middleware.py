"""
Django middleware for binding request context to structlog.

This middleware automatically adds request_id and user_id to all log entries
for the duration of a request.
"""

import structlog
from uuid import uuid4


class StructlogRequestContextMiddleware:
    """
    Middleware to bind request context (request_id, user_id) to structlog.
    
    This ensures all log entries during a request include correlation IDs
    for tracing requests across the system.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Generate unique request ID
        request_id = uuid4().hex
        
        # Bind context variables for this request
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            user_id=request.user.id if request.user.is_authenticated else None,
        )
        
        try:
            response = self.get_response(request)
            return response
        finally:
            # Clear context after request completes
            structlog.contextvars.clear_contextvars()


"""
Exception handler for Django REST Framework.

This module provides a custom exception handler that converts our custom
exceptions to consistent API responses.
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from .exceptions import BaseAPIException, FormValidationException


def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF that handles our custom exceptions.
    
    Args:
        exc: The exception instance
        context: The context dictionary
        
    Returns:
        Response object with error details
    """
    # Handle our custom exceptions
    if isinstance(exc, BaseAPIException):
        response_data = exc.to_dict()
        
        # For FormValidationException, ensure form data is included in response
        if isinstance(exc, FormValidationException):
            # Form data is already in extra_data, but ensure it's at top level for frontend
            if 'form' not in response_data and exc.form_data:
                response_data['form'] = exc.form_data
        
        return Response(
            response_data,
            status=exc.status_code
        )
    
    # Let DRF handle other exceptions
    response = exception_handler(exc, context)
    
    # Customize DRF's default error response format
    if response is not None:
        custom_response_data = {
            'error': str(exc),
            'detail': response.data.get('detail', str(exc)) if isinstance(response.data, dict) else str(response.data),
        }
        
        # Add field errors if present
        if isinstance(response.data, dict) and 'detail' not in response.data:
            # This might be a validation error with field details
            if any(key != 'detail' for key in response.data.keys()):
                custom_response_data['errors'] = response.data
        
        response.data = custom_response_data
    
    return response


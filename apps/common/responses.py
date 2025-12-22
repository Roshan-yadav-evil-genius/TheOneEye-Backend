"""
Standardized response helpers for consistent API responses.
"""
from typing import Dict, Any, Optional
from rest_framework.response import Response
from rest_framework import status
from .exceptions import AppException


def success_response(
    data: Any = None,
    message: Optional[str] = None,
    status_code: int = status.HTTP_200_OK
) -> Response:
    """
    Create a standardized success response.
    
    Args:
        data: Response data
        message: Optional success message
        status_code: HTTP status code
        
    Returns:
        Response object
    """
    response_data: Dict[str, Any] = {}
    
    if data is not None:
        response_data['data'] = data
    
    if message:
        response_data['message'] = message
    
    return Response(response_data, status=status_code)


def error_response(
    message: str,
    errors: Optional[Dict] = None,
    status_code: int = status.HTTP_400_BAD_REQUEST
) -> Response:
    """
    Create a standardized error response.
    
    Args:
        message: Error message
        errors: Optional dictionary of field-specific errors
        status_code: HTTP status code
        
    Returns:
        Response object
    """
    response_data: Dict[str, Any] = {
        'error': message
    }
    
    if errors:
        response_data['errors'] = errors
    
    return Response(response_data, status=status_code)


def exception_response(exception: AppException) -> Response:
    """
    Create a standardized error response from an AppException.
    
    Args:
        exception: AppException instance
        
    Returns:
        Response object
    """
    response_data: Dict[str, Any] = {
        'error': exception.message
    }
    
    if hasattr(exception, 'errors') and exception.errors:
        response_data['errors'] = exception.errors
    
    return Response(response_data, status=exception.status_code)


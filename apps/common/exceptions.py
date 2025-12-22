"""
Custom exceptions for the application.
Provides standardized exception classes for consistent error handling.
"""
from rest_framework import status


class AppException(Exception):
    """Base exception for application-specific errors."""
    
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ValidationException(AppException):
    """Exception for validation errors."""
    
    def __init__(self, message: str, errors: dict = None):
        self.errors = errors or {}
        super().__init__(message, status.HTTP_400_BAD_REQUEST)


class AuthenticationException(AppException):
    """Exception for authentication errors."""
    
    def __init__(self, message: str = 'Authentication failed'):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)


class AuthorizationException(AppException):
    """Exception for authorization errors."""
    
    def __init__(self, message: str = 'Permission denied'):
        super().__init__(message, status.HTTP_403_FORBIDDEN)


class NotFoundException(AppException):
    """Exception for resource not found errors."""
    
    def __init__(self, message: str = 'Resource not found'):
        super().__init__(message, status.HTTP_404_NOT_FOUND)


class ConflictException(AppException):
    """Exception for resource conflict errors."""
    
    def __init__(self, message: str = 'Resource conflict'):
        super().__init__(message, status.HTTP_409_CONFLICT)


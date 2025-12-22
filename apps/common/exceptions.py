"""
Common exceptions for the application.

This module defines custom exception classes for consistent error handling
across the application. All exceptions follow a standard format.
"""

from typing import Optional, Dict, Any


class BaseAPIException(Exception):
    """
    Base exception class for all API-related errors.
    Provides consistent error response format.
    """
    
    def __init__(
        self,
        message: str,
        detail: Optional[str] = None,
        status_code: int = 500,
        error_code: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the exception.
        
        Args:
            message: Human-readable error message
            detail: Detailed error information
            status_code: HTTP status code
            error_code: Application-specific error code
            extra_data: Additional error data
        """
        self.message = message
        self.detail = detail or message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.extra_data = extra_data or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary for API response.
        
        Returns:
            Dictionary with error information
        """
        result = {
            'error': self.message,
            'detail': self.detail,
            'error_code': self.error_code,
        }
        if self.extra_data:
            result.update(self.extra_data)
        return result


class ValidationError(BaseAPIException):
    """Exception for validation errors (400 Bad Request)."""
    
    def __init__(self, message: str, detail: Optional[str] = None, extra_data: Optional[Dict[str, Any]] = None):
        super().__init__(message, detail, 400, 'ValidationError', extra_data)


class NotFoundError(BaseAPIException):
    """Exception for resource not found errors (404 Not Found)."""
    
    def __init__(self, message: str, detail: Optional[str] = None, resource_type: Optional[str] = None):
        extra_data = {'resource_type': resource_type} if resource_type else {}
        super().__init__(message, detail, 404, 'NotFoundError', extra_data)


class UnauthorizedError(BaseAPIException):
    """Exception for authentication errors (401 Unauthorized)."""
    
    def __init__(self, message: str = 'Authentication required', detail: Optional[str] = None):
        super().__init__(message, detail, 401, 'UnauthorizedError')


class ForbiddenError(BaseAPIException):
    """Exception for authorization errors (403 Forbidden)."""
    
    def __init__(self, message: str = 'Permission denied', detail: Optional[str] = None):
        super().__init__(message, detail, 403, 'ForbiddenError')


class InternalServerError(BaseAPIException):
    """Exception for internal server errors (500 Internal Server Error)."""
    
    def __init__(self, message: str = 'An internal error occurred', detail: Optional[str] = None):
        super().__init__(message, detail, 500, 'InternalServerError')


class NodeTypeNotFoundError(NotFoundError):
    """Exception for node type not found errors."""
    
    def __init__(self, node_type: str):
        super().__init__(
            f'Node type not found: {node_type}',
            f'The node type "{node_type}" is not registered in the system',
            resource_type='NodeType'
        )
        self.node_type = node_type


class NodeNotFoundError(NotFoundError):
    """Exception for node not found errors."""
    
    def __init__(self, node_id: str, workflow_id: Optional[str] = None):
        message = f'Node not found: {node_id}'
        if workflow_id:
            message += f' in workflow {workflow_id}'
        super().__init__(message, message, resource_type='Node')
        self.node_id = node_id
        self.workflow_id = workflow_id


class WorkflowNotFoundError(NotFoundError):
    """Exception for workflow not found errors."""
    
    def __init__(self, workflow_id: str):
        super().__init__(
            f'Workflow not found: {workflow_id}',
            f'The workflow with ID "{workflow_id}" does not exist',
            resource_type='Workflow'
        )
        self.workflow_id = workflow_id


# Backward compatibility alias
AppException = BaseAPIException

"""
Custom exceptions for Form dependency management.
"""


class FormDependencyError(Exception):
    """Base exception for form dependency errors."""
    pass


class MissingDependencyError(FormDependencyError):
    """Raised when a field depends on a non-existent field."""
    pass


class SelfReferenceError(FormDependencyError):
    """Raised when a field depends on itself."""
    pass


class MissingLoaderError(FormDependencyError):
    """Raised when no loader is defined for a dependent field."""
    pass


class NonCallableLoaderError(FormDependencyError):
    """Raised when the loader is not callable."""
    pass

"""
Common configuration utilities for backend applications.
Provides shared configuration helpers.
"""
import os
from typing import List


def get_env_list(key: str, default: str = '') -> List[str]:
    """
    Get environment variable as a comma-separated list.
    
    Args:
        key: Environment variable key
        default: Default value if key is not set
        
    Returns:
        List of strings
    """
    value = os.environ.get(key, default)
    return [item.strip() for item in value.split(',') if item.strip()]


def get_env_bool(key: str, default: bool = False) -> bool:
    """
    Get environment variable as boolean.
    
    Args:
        key: Environment variable key
        default: Default value if key is not set
        
    Returns:
        Boolean value
    """
    value = os.environ.get(key, str(default)).lower()
    return value in ('true', '1', 'yes', 'on')


def get_env_int(key: str, default: int = 0) -> int:
    """
    Get environment variable as integer.
    
    Args:
        key: Environment variable key
        default: Default value if key is not set
        
    Returns:
        Integer value
    """
    try:
        return int(os.environ.get(key, str(default)))
    except ValueError:
        return default


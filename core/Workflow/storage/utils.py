"""
Storage Utilities

Shared utility functions for storage operations.
"""

import json
from typing import Any, Optional


def serialize(data: Any) -> str:
    """
    Serialize data to JSON string.
    
    Args:
        data: Data to serialize (dict, list, or any JSON-serializable type)
        
    Returns:
        JSON string representation of the data
    """
    return json.dumps(data)


def deserialize(data: Optional[str]) -> Optional[Any]:
    """
    Deserialize JSON string to Python object.
    
    Args:
        data: JSON string to deserialize, or None
        
    Returns:
        Deserialized Python object, or None if input is None
    """
    if data is None:
        return None
    return json.loads(data)


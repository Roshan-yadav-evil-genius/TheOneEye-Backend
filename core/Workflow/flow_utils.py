"""
Utility functions and classes for flow management.
"""


from Node.Core.Node.Core import BaseNode
from Node.Core.Node.Core.BaseNode import ProducerNode, NonBlockingNode, ConditionalNode, BlockingNode
from typing import Optional


class BranchKeyNormalizer:
    """
    Utility class for normalizing branch keys between different formats.
    Handles conversion between lowercase internal format and capitalized display format.
    """
    
    @staticmethod
    def normalize_to_lowercase(source_handle: any) -> str:
        """
        Normalize edge key from sourceHandle to lowercase format.
        
        Args:
            source_handle: Source handle value (Yes/No label or null)
            
        Returns:
            Normalized key string ("yes", "no", or "default")
        """
        if source_handle:
            return source_handle.lower()
        return "default"
    
    @staticmethod
    def normalize_to_capitalized(branch_key: str) -> str:
        """
        Convert lowercase branch key to capitalized format for display.
        
        Args:
            branch_key: Lowercase branch key ("yes", "no", "default", or other)
            
        Returns:
            Capitalized label ("Yes", "No", None for default, or original key)
        """
        if branch_key == "default":
            return None
        elif branch_key == "yes":
            return "Yes"
        elif branch_key == "no":
            return "No"
        else:
            return branch_key
    
    @staticmethod
    def normalize_for_display(branch_key: str) -> str:
        """
        Normalize branch key for display purposes.
        Returns the capitalized version or "default" if None.
        
        Args:
            branch_key: Branch key in any format
            
        Returns:
            Display-friendly label string
        """
        capitalized = BranchKeyNormalizer.normalize_to_capitalized(branch_key)
        return capitalized or "default"


def node_type(base_node_instance: BaseNode) -> Optional[str]:
    """
    Get the type name of a BaseNode instance.
    
    Args:
        base_node_instance: The node instance to check
        
    Returns:
        The type name string or None if unknown
    """
    if isinstance(base_node_instance, ProducerNode):
        return ProducerNode.__name__
    elif isinstance(base_node_instance, NonBlockingNode):
        return NonBlockingNode.__name__
    elif isinstance(base_node_instance, ConditionalNode):
        return ConditionalNode.__name__
    elif isinstance(base_node_instance, BlockingNode):
        return BlockingNode.__name__
    else:
        return None

"""
Services Package
Provides business logic services for node operations.
"""

from pathlib import Path
from typing import Optional

from .node_registry import NodeRegistry
from .node_loader import NodeLoader
from .form_loader import FormLoader
from .node_executor import NodeExecutor


class ServiceContainer:
    """
    Container for all application services.
    Provides dependency injection and lazy initialization.
    """
    
    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize service container.
        
        Args:
            project_root: Root directory of the project.
                         Defaults to NewDesign folder.
        """
        if project_root is None:
            # Default: views/services -> NewDesign
            project_root = Path(__file__).parent.parent.parent
        
        self._project_root = project_root
        
        # Lazy-initialized services
        self._node_registry: Optional[NodeRegistry] = None
        self._node_loader: Optional[NodeLoader] = None
        self._form_loader: Optional[FormLoader] = None
        self._node_executor: Optional[NodeExecutor] = None
    
    @property
    def node_registry(self) -> NodeRegistry:
        """Get or create NodeRegistry instance."""
        if self._node_registry is None:
            from ..scanner import create_scanner
            scanner = create_scanner()
            self._node_registry = NodeRegistry(scanner)
        return self._node_registry
    
    @property
    def node_loader(self) -> NodeLoader:
        """Get or create NodeLoader instance."""
        if self._node_loader is None:
            self._node_loader = NodeLoader(self._project_root)
        return self._node_loader
    
    @property
    def form_loader(self) -> FormLoader:
        """Get or create FormLoader instance."""
        if self._form_loader is None:
            self._form_loader = FormLoader(self.node_loader)
        return self._form_loader
    
    @property
    def node_executor(self) -> NodeExecutor:
        """Get or create NodeExecutor instance."""
        if self._node_executor is None:
            self._node_executor = NodeExecutor(self.node_loader)
        return self._node_executor


def create_services(project_root: Optional[Path] = None) -> ServiceContainer:
    """
    Factory function to create a service container.
    
    Args:
        project_root: Optional project root path.
        
    Returns:
        ServiceContainer with all services configured.
    """
    return ServiceContainer(project_root)


__all__ = [
    'ServiceContainer',
    'NodeRegistry',
    'NodeLoader',
    'FormLoader',
    'NodeExecutor',
    'create_services',
]


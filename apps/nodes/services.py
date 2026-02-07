"""
Node Services Module
Singleton wrapper for the ServiceContainer from core/views.
"""

import sys
from pathlib import Path
from typing import Optional

# Add backend to the Python path so core.views and core.Node resolve
# backend/apps/nodes/services.py -> BASE_DIR = backend
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.views.services import ServiceContainer, create_services
from core.views.scanner import create_scanner

class NodeServices:
    """
    Singleton wrapper for node services in Django.
    Provides thread-safe lazy initialization.
    """
    
    _instance: Optional['NodeServices'] = None
    _services: Optional[ServiceContainer] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @property
    def services(self) -> ServiceContainer:
        """Get or create the ServiceContainer instance."""
        if self._services is None:
            # Use backend as project root so NodeLoader builds paths like core.Node.Nodes.*
            # (avoids backend.core.Node which breaks relative imports in BaseNode)
            self._services = create_services(BASE_DIR)
        return self._services
    
    @property
    def node_registry(self):
        """Get the NodeRegistry instance."""
        return self.services.node_registry
    
    @property
    def form_loader(self):
        """Get the FormLoader instance."""
        return self.services.form_loader
    
    @property
    def node_executor(self):
        """Get the NodeExecutor instance."""
        return self.services.node_executor
    
    def refresh(self):
        """Refresh the node registry cache."""
        self.node_registry.refresh()


def get_node_services() -> NodeServices:
    """
    Factory function to get the singleton NodeServices instance.
    
    Returns:
        NodeServices: The singleton instance.
    """
    return NodeServices()


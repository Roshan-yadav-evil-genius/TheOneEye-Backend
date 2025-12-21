"""
Node Services Module
Singleton wrapper for the ServiceContainer from core/views.
"""

import sys
from pathlib import Path
from typing import Optional

# Add core to the Python path to import views services
# Calculate core path: backend/apps/nodes/services.py -> backend/core
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CORE_PATH = BASE_DIR / 'core'

if str(CORE_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_PATH))

from views.services import ServiceContainer, create_services
from views.scanner import create_scanner

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
            # Project root should be Attempt3 (parent of backend), not backend/core itself
            PROJECT_ROOT = BASE_DIR.parent
            self._services = create_services(PROJECT_ROOT)
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


"""
Node Loader Module
Dynamically loads node classes from file paths.
"""

import importlib
import sys
from pathlib import Path
from typing import Dict, Optional, Type


class NodeLoader:
    """
    Dynamically loads node classes from their file paths.
    
    Responsibilities:
    - Convert file paths to module paths
    - Dynamically import modules
    - Load node classes from modules
    """
    
    def __init__(self, project_root: Path):
        """
        Initialize NodeLoader.
        
        Args:
            project_root: Root directory of the project (NewDesign folder).
        """
        self._project_root = project_root
        self._ensure_path_in_sys()
    
    def _ensure_path_in_sys(self) -> None:
        """Ensure project root is in sys.path for imports."""
        project_root_str = str(self._project_root)
        if project_root_str not in sys.path:
            sys.path.insert(0, project_root_str)
    
    def load_class(self, node_metadata: Dict) -> Optional[Type]:
        """
        Load a node class from its metadata.
        
        Args:
            node_metadata: Dict containing 'file_path' and 'name' keys.
            
        Returns:
            The node class or None if loading fails.
        """
        file_path = node_metadata.get('file_path')
        class_name = node_metadata.get('name')
        
        if not file_path or not class_name:
            return None
        
        try:
            module = self._import_module(Path(file_path))
            if module is None:
                return None
            
            node_class = getattr(module, class_name, None)
            return node_class
            
        except Exception as e:
            print(f"Error loading node class from {file_path}: {e}")
            return None
    
    def _import_module(self, file_path: Path):
        """
        Import a module from a file path.
        
        Args:
            file_path: Path to the Python file.
            
        Returns:
            The imported module or None if import fails.
        """
        try:
            relative_path = file_path.relative_to(self._project_root)
            module_path = str(relative_path.with_suffix('')).replace('\\', '.').replace('/', '.')
            return importlib.import_module(module_path)
        except Exception as e:
            print(f"Error importing module from {file_path}: {e}")
            return None
    
    def _get_module_path(self, file_path: Path) -> str:
        """
        Convert a file path to a Python module path.
        
        Args:
            file_path: Path to the Python file.
            
        Returns:
            Dotted module path string.
        """
        relative_path = file_path.relative_to(self._project_root)
        return str(relative_path.with_suffix('')).replace('\\', '.').replace('/', '.')


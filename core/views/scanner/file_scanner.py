"""
File Scanner Module
Scans individual Python files for node class definitions.
"""

import ast
from pathlib import Path
from typing import Dict, List, Optional

from .metadata_extractor import MetadataExtractor


# Supported icon file extensions
ICON_EXTENSIONS = ['.png', '.jpg', '.jpeg']


class FileScanner:
    """
    Scans Python files and extracts node metadata.
    
    Responsibilities:
    - Read and parse Python files
    - Use MetadataExtractor to extract class metadata
    - Discover node icons (auto-discovery)
    - Handle file I/O errors gracefully
    """
    
    def __init__(self, extractor: MetadataExtractor, nodes_base_path: Optional[Path] = None):
        """
        Initialize FileScanner with a metadata extractor.
        
        Args:
            extractor: MetadataExtractor instance for extracting class metadata.
            nodes_base_path: Base path to Nodes folder for computing relative icon paths.
        """
        self._extractor = extractor
        self._nodes_base_path = nodes_base_path
    
    def set_nodes_base_path(self, nodes_base_path: Path) -> None:
        """Set the base path for computing relative icon paths."""
        self._nodes_base_path = nodes_base_path
    
    def scan_file(self, file_path: Path) -> List[Dict]:
        """
        Scan a Python file and extract all node class metadata.
        
        Args:
            file_path: Path to the Python file to scan.
            
        Returns:
            List of node metadata dictionaries found in the file.
        """
        nodes = []
        
        try:
            source = self._read_file(file_path)
            tree = ast.parse(source)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    metadata = self._extractor.extract_from_class(node)
                    if metadata:
                        metadata['file'] = file_path.name
                        metadata['file_path'] = str(file_path)
                        # Auto-discover icon in same directory
                        metadata['icon'] = self._discover_icon(file_path)
                        nodes.append(metadata)
        
        except (SyntaxError, FileNotFoundError, PermissionError) as e:
            print(f"Error scanning {file_path}: {e}")
        
        return nodes
    
    def _discover_icon(self, file_path: Path) -> Optional[str]:
        """
        Discover icon file in the same directory as the node file.
        
        Looks for icon.png, icon.jpg, icon.jpeg in the node's directory.
        Returns a relative path from nodes base for static file serving.
        
        Args:
            file_path: Path to the node Python file.
            
        Returns:
            Relative icon path (e.g., "Store/icon.png") or None if not found.
        """
        node_dir = file_path.parent
        
        for ext in ICON_EXTENSIONS:
            icon_file = node_dir / f"icon{ext}"
            if icon_file.exists():
                # Return relative path from nodes base
                if self._nodes_base_path:
                    try:
                        relative_path = icon_file.relative_to(self._nodes_base_path)
                        return str(relative_path)
                    except ValueError:
                        # Not relative to nodes base, return absolute
                        return str(icon_file)
                return str(icon_file)
        
        return None
    
    def _read_file(self, file_path: Path) -> str:
        """
        Read file contents with UTF-8 encoding.
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()


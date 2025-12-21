"""
Directory Scanner Module
Traverses directory structures and builds hierarchical node trees.
"""

from pathlib import Path
from typing import Dict, Optional

from .file_scanner import FileScanner
from .tree_utils import count_nodes, prune_empty_folders


class DirectoryScanner:
    """
    Scans directories and builds hierarchical node trees.
    
    Responsibilities:
    - Traverse directory structures
    - Build hierarchical tree of folders and nodes
    - Skip hidden directories and __pycache__
    - Prune empty folders from results
    """
    
    # Directories to skip during scanning
    SKIP_PREFIXES = ('_', '.')
    
    def __init__(self, file_scanner: FileScanner):
        """
        Initialize DirectoryScanner with a file scanner.
        
        Args:
            file_scanner: FileScanner instance for scanning Python files.
        """
        self._file_scanner = file_scanner
    
    def scan_directory(self, directory: Path) -> Dict:
        """
        Recursively scan a directory and build a hierarchical tree structure.
        
        Args:
            directory: Path to directory to scan.
            
        Returns:
            Dict with 'nodes' (list) and 'subfolders' (dict).
        """
        result = {
            'nodes': [],
            'subfolders': {}
        }
        
        # Scan Python files in this directory
        for item in directory.iterdir():
            if item.is_file() and item.suffix == '.py':
                if item.name == '__init__.py':
                    continue
                
                nodes = self._file_scanner.scan_file(item)
                result['nodes'].extend(nodes)
        
        # Recursively scan subdirectories
        for subdir in directory.iterdir():
            if not subdir.is_dir():
                continue
            
            if self._should_skip(subdir.name):
                continue
            
            subfolder_result = self.scan_directory(subdir)
            result['subfolders'][subdir.name] = subfolder_result
        
        return result
    
    def scan_nodes_folder(self, nodes_path: Optional[Path] = None) -> Dict[str, Dict]:
        """
        Scan the Nodes folder and return all nodes in a hierarchical tree.
        
        Args:
            nodes_path: Optional custom path to Nodes folder.
                       Defaults to Node/Nodes relative to views package.
        
        Returns:
            Dict with category names as keys and nested folder structures as values.
        """
        if nodes_path is None:
            # Default path relative to this file (views/scanner -> NewDesign)
            base_dir = Path(__file__).parent.parent.parent
            nodes_path = base_dir / 'Node' / 'Nodes'
        
        if not nodes_path.exists():
            return {}
        
        # Set nodes base path for icon discovery
        self._file_scanner.set_nodes_base_path(nodes_path)
        
        grouped_nodes = {}
        
        # Scan top-level subdirectories (categories)
        for category_dir in nodes_path.iterdir():
            if not category_dir.is_dir():
                continue
            
            if self._should_skip(category_dir.name):
                continue
            
            category_result = self.scan_directory(category_dir)
            grouped_nodes[category_dir.name] = category_result
        
        # Prune empty folders and categories
        return self._prune_empty_categories(grouped_nodes)
    
    def _should_skip(self, name: str) -> bool:
        """
        Check if a directory should be skipped.
        """
        return any(name.startswith(prefix) for prefix in self.SKIP_PREFIXES)
    
    def _prune_empty_categories(self, grouped_nodes: Dict[str, Dict]) -> Dict[str, Dict]:
        """
        Remove empty categories and prune empty subfolders.
        """
        pruned = {}
        
        for category_name, category_data in grouped_nodes.items():
            pruned_category = prune_empty_folders(category_data)
            if count_nodes(pruned_category) > 0:
                pruned[category_name] = pruned_category
        
        return pruned


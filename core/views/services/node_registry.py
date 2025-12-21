"""
Node Registry Module
Central registry for node lookup and caching.
"""

from typing import Dict, List, Optional

from ..scanner import DirectoryScanner, count_nodes, flatten_nodes, collapse_node_containers


class NodeRegistry:
    """
    Central registry for node lookup with caching.
    
    Responsibilities:
    - Cache scanned node data
    - Provide node lookup by identifier
    - Provide various views of node data (tree, flat, count)
    """
    
    def __init__(self, scanner: DirectoryScanner):
        """
        Initialize NodeRegistry with a directory scanner.
        
        Args:
            scanner: DirectoryScanner for scanning nodes.
        """
        self._scanner = scanner
        self._cache: Optional[Dict[str, Dict]] = None
        self._flat_cache: Optional[List[Dict]] = None
    
    def get_all_nodes(self) -> Dict[str, Dict]:
        """
        Get all nodes as a hierarchical tree structure.
        
        Returns:
            Dict with category names as keys and folder structures as values.
            Node container folders are collapsed so nodes appear directly in categories.
        """
        if self._cache is None:
            raw_tree = self._scanner.scan_nodes_folder()
            # Collapse node container folders (e.g., StaticDelay/) to lift nodes up
            self._cache = {
                category: collapse_node_containers(folder_data)
                for category, folder_data in raw_tree.items()
            }
        return self._cache
    
    def get_nodes_flat(self) -> List[Dict]:
        """
        Get all nodes as a flat list.
        
        Returns:
            List of node metadata dictionaries with 'category' field.
        """
        if self._flat_cache is None:
            nodes = self.get_all_nodes()
            self._flat_cache = []
            for category, folder_data in nodes.items():
                self._flat_cache.extend(flatten_nodes(folder_data, category))
        return self._flat_cache
    
    def find_by_identifier(self, identifier: str) -> Optional[Dict]:
        """
        Find a node by its identifier.
        
        Args:
            identifier: The node identifier to search for.
            
        Returns:
            Node metadata dict or None if not found.
        """
        nodes = self.get_nodes_flat()
        for node in nodes:
            if node.get('identifier') == identifier:
                return node
        return None
    
    def get_count(self) -> int:
        """
        Get total count of all nodes.
        
        Returns:
            Total number of nodes.
        """
        nodes = self.get_all_nodes()
        total = 0
        for folder_data in nodes.values():
            total += count_nodes(folder_data)
        return total
    
    def refresh(self) -> None:
        """
        Clear cache and force rescan on next access.
        """
        self._cache = None
        self._flat_cache = None


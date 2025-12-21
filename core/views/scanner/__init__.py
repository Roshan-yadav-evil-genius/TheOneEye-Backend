"""
Scanner Package
Provides functionality to scan and extract node metadata from Python files.
"""

from .metadata_extractor import MetadataExtractor
from .file_scanner import FileScanner
from .directory_scanner import DirectoryScanner
from .tree_utils import count_nodes, prune_empty_folders, flatten_nodes, collapse_node_containers


def create_scanner() -> DirectoryScanner:
    """
    Factory function to create a fully configured DirectoryScanner.
    
    Returns:
        DirectoryScanner: Ready-to-use scanner instance.
    """
    extractor = MetadataExtractor()
    file_scanner = FileScanner(extractor)
    return DirectoryScanner(file_scanner)


__all__ = [
    'MetadataExtractor',
    'FileScanner',
    'DirectoryScanner',
    'create_scanner',
    'count_nodes',
    'prune_empty_folders',
    'flatten_nodes',
    'collapse_node_containers',
]


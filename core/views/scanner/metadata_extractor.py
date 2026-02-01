"""
Metadata Extractor Module
Extracts node class metadata from Python AST.
"""

import ast
from typing import Dict, Optional


class MetadataExtractor:
    """
    Extracts node metadata from Python AST class definitions.
    
    Responsibilities:
    - Parse AST class nodes to extract node information
    - Extract identifier, form class, label, and description
    - Determine node type from base class inheritance
    """
    
    # Known base node types that we scan for
    NODE_BASE_TYPES = {
        'BlockingNode',
        'NonBlockingNode',
        'ProducerNode',
        'LogicalNode',
        'ConditionalNode',
        'LoopNode',
        'BaseNode',
        'QueueNode',
        'QueueReader'
    }
    
    def extract_from_class(self, class_node: ast.ClassDef) -> Optional[Dict]:
        """
        Extract metadata from a class definition.
        
        Args:
            class_node: AST ClassDef node to extract metadata from.
            
        Returns:
            Dict with node metadata or None if not a valid node class.
        """
        node_type = self._get_node_type(class_node)
        if not node_type:
            return None
        
        identifier = self._extract_identifier(class_node)
        form_class = self._extract_form_class_name(class_node)
        label = self._extract_property_string(class_node, 'label')
        description = self._extract_property_string(class_node, 'description')
        
        # Get port configuration based on node type
        ports = self._get_default_ports(node_type)
        
        return {
            'name': class_node.name,
            'identifier': identifier or class_node.name.lower(),
            'type': node_type,
            'has_form': form_class is not None,
            'form_class': form_class,
            'label': label,
            'description': description,
            'input_ports': ports['input_ports'],
            'output_ports': ports['output_ports'],
        }
    
    def _get_node_type(self, class_node: ast.ClassDef) -> Optional[str]:
        """
        Determine the node type from base class inheritance.
        
        Returns:
            Node type string or None if not a recognized node class.
        """
        for base in class_node.bases:
            base_name = None
            if isinstance(base, ast.Name):
                base_name = base.id
            elif isinstance(base, ast.Attribute):
                base_name = base.attr
            
            if base_name and base_name in self.NODE_BASE_TYPES:
                return base_name
        
        return None
    
    def _extract_identifier(self, class_node: ast.ClassDef) -> Optional[str]:
        """
        Extract the identifier from the identifier() method.
        """
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == 'identifier':
                return self._extract_string_from_return(item)
        return None
    
    def _extract_string_from_return(self, node: ast.FunctionDef) -> Optional[str]:
        """
        Extract a string return value from a method.
        """
        for stmt in node.body:
            if isinstance(stmt, ast.Return) and stmt.value:
                if isinstance(stmt.value, ast.Constant):
                    return stmt.value.value
        return None
    
    def _extract_form_class_name(self, class_node: ast.ClassDef) -> Optional[str]:
        """
        Extract form class name from get_form() method.
        Looks for pattern: return FormClassName()
        """
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == 'get_form':
                for stmt in item.body:
                    if isinstance(stmt, ast.Return) and stmt.value:
                        if isinstance(stmt.value, ast.Call):
                            if isinstance(stmt.value.func, ast.Name):
                                form_class = stmt.value.func.id
                                return form_class
        return None
    
    def _extract_property_string(self, class_node: ast.ClassDef, prop_name: str) -> Optional[str]:
        """
        Extract a string value from a @property decorated method.
        """
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == prop_name:
                # Check if it has @property decorator
                for decorator in item.decorator_list:
                    if isinstance(decorator, ast.Name) and decorator.id == 'property':
                        return self._extract_string_from_return(item)
        return None

    def _get_default_ports(self, node_type: str) -> dict:
        """
        Get default port configuration based on node type.
        
        Args:
            node_type: The base class type of the node.
            
        Returns:
            Dict with 'input_ports' and 'output_ports' lists.
        """
        input_ports = [{"id": "default", "label": "In"}]
        output_ports = [{"id": "default", "label": "Out"}]
        
        if node_type == 'ProducerNode':
            # Producer nodes have no input - they start the flow
            input_ports = []
        elif node_type == 'ConditionalNode':
            # Conditional nodes have yes/no output branches
            output_ports = [
                {"id": "yes", "label": "Yes"},
                {"id": "no", "label": "No"}
            ]
        elif node_type == 'LoopNode':
            # Loop nodes have default (outgoing) and subdag (body entry) output branches
            output_ports = [
                {"id": "default", "label": "Out"},
                {"id": "subdag", "label": "Body"}
            ]

        return {'input_ports': input_ports, 'output_ports': output_ports}


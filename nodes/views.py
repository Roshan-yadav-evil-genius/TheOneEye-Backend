"""
Node API Views Module
REST API endpoints for node operations (mirrors core/views/routes/api.py).
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework import status

from .services import get_node_services


class NodeListView(APIView):
    """
    Get all nodes as a hierarchical tree structure.
    
    GET /api/nodes/
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        services = get_node_services()
        nodes = services.node_registry.get_all_nodes()
        return Response(nodes)


class NodeFlatListView(APIView):
    """
    Get all nodes as a flat list.
    
    GET /api/nodes/flat/
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        services = get_node_services()
        nodes = services.node_registry.get_nodes_flat()
        return Response(nodes)


class NodeCountView(APIView):
    """
    Get total count of all nodes.
    
    GET /api/nodes/count/
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        services = get_node_services()
        count = services.node_registry.get_count()
        return Response({'count': count})


class NodeRefreshView(APIView):
    """
    Refresh the node registry cache.
    
    POST /api/nodes/refresh/
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        services = get_node_services()
        services.refresh()
        return Response({'message': 'Node cache refreshed successfully'})


class NodeFormView(APIView):
    """
    Get form JSON for a specific node.
    
    GET /api/nodes/<identifier>/form/
    """
    permission_classes = [AllowAny]
    
    def get(self, request, identifier):
        services = get_node_services()
        
        # Find the node by identifier
        node = services.node_registry.find_by_identifier(identifier)
        
        if node is None:
            return Response(
                {'error': 'Node not found', 'identifier': identifier},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if node has a form
        if not node.get('has_form'):
            return Response({
                'node': _format_node_response(node),
                'form': None,
                'message': 'This node does not have a form'
            })
        
        # Load and serialize the form
        form_json = services.form_loader.load_form(node)
        
        return Response({
            'node': _format_node_response(node, include_form_class=True),
            'form': form_json
        })


class NodeExecuteView(APIView):
    """
    Execute a node with given input data and form values.
    
    POST /api/nodes/<identifier>/execute/
    
    Request body:
    {
        "input_data": { ... },
        "form_data": { ... }
    }
    """
    permission_classes = [AllowAny]
    
    def post(self, request, identifier):
        services = get_node_services()
        
        # Find the node by identifier
        node = services.node_registry.find_by_identifier(identifier)
        
        if node is None:
            return Response(
                {'error': 'Node not found', 'identifier': identifier},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Parse request data
        input_data = request.data.get('input_data', {})
        form_data = request.data.get('form_data', {})
        
        # Execute the node
        result = services.node_executor.execute(node, input_data, form_data)
        
        if not result.get('success'):
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(result)


class NodeFieldOptionsView(APIView):
    """
    Get options for a dependent field based on parent field value.
    
    POST /api/nodes/<identifier>/field-options/
    
    Request body:
    {
        "parent_field": "country",
        "parent_value": "india",
        "dependent_field": "state",
        "form_values": {"country": "india", ...}  // Optional: all current form values
    }
    
    Returns:
    {
        "field": "state",
        "options": [{"value": "maharashtra", "text": "Maharashtra"}, ...]
    }
    """
    permission_classes = [AllowAny]
    
    def post(self, request, identifier):
        services = get_node_services()
        
        # Find the node by identifier
        node = services.node_registry.find_by_identifier(identifier)
        
        if node is None:
            return Response(
                {'error': 'Node not found', 'identifier': identifier},
                status=status.HTTP_404_NOT_FOUND
            )
        
        parent_field = request.data.get('parent_field')
        parent_value = request.data.get('parent_value')
        dependent_field = request.data.get('dependent_field')
        form_values = request.data.get('form_values', {})
        
        if not all([parent_field, dependent_field]):
            return Response(
                {'error': 'parent_field and dependent_field are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get field options from form, passing all form values for multi-parent access
        options = services.form_loader.get_field_options(
            node, dependent_field, parent_value, form_values
        )
        
        return Response({
            'field': dependent_field,
            'options': [{'value': v, 'text': t} for v, t in options]
        })


class NodeDetailView(APIView):
    """
    Get details for a specific node by identifier.
    
    GET /api/nodes/<identifier>/
    """
    permission_classes = [AllowAny]
    
    def get(self, request, identifier):
        services = get_node_services()
        
        # Find the node by identifier
        node = services.node_registry.find_by_identifier(identifier)
        
        if node is None:
            return Response(
                {'error': 'Node not found', 'identifier': identifier},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(_format_node_response(node, include_form_class=True, include_file_path=True))


def _format_node_response(node: dict, include_form_class: bool = False, include_file_path: bool = False) -> dict:
    """
    Format node metadata for API response.
    """
    response = {
        'name': node.get('name'),
        'identifier': node.get('identifier'),
        'type': node.get('type'),
        'label': node.get('label'),
        'description': node.get('description'),
        'has_form': node.get('has_form'),
        'category': node.get('category'),
    }
    
    if include_form_class:
        response['form_class'] = node.get('form_class')
    
    if include_file_path:
        response['file_path'] = node.get('file_path')
    
    return response

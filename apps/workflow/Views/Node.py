from django.shortcuts import get_object_or_404
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from apps.workflow.models import Node, WorkFlow
from apps.workflow.Serializers import NodeSerializer
from apps.workflow.Serializers.Canvas import CanvasNodeSerializer
from apps.workflow.services import dependency_service, node_service


class NodeViewSet(ModelViewSet):
    serializer_class = NodeSerializer

    def get_queryset(self):
        workflow_pk = self.kwargs.get("workflow_pk")
        if workflow_pk:
            return Node.objects.filter(workflow_id=workflow_pk)
        return Node.objects.all()
    
    def get_workflow(self):
        """Get the workflow from URL kwargs"""
        workflow_pk = self.kwargs.get('workflow_pk')
        return get_object_or_404(WorkFlow, id=workflow_pk)
    
    def perform_create(self, serializer):
        workflow = self.get_workflow()
        serializer.save(workflow=workflow)
        
    def get_serializer_class(self):
        return NodeSerializer

    @action(detail=True, methods=['get'], url_path='input')
    def get_input(self, request, workflow_pk=None, pk=None):
        """Get aggregated input data from all connected source nodes"""
        node = self.get_object()
        input_data = dependency_service.get_node_input_payload(str(node.id))
        return Response(input_data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='output')
    def get_output(self, request, workflow_pk=None, pk=None):
        """Get the output data for this node"""
        node = self.get_object()
        return Response(node.config, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='add')
    def add_node(self, request, workflow_pk=None):
        """
        Add a node to the workflow canvas.
        View only handles HTTP request/response, delegates to service.
        """
        workflow = self.get_workflow()
        
        # Extract request data
        node_type = request.data.get('nodeTemplate', 'custom-node')
        position = request.data.get('position', {'x': 0, 'y': 0})
        form_values = request.data.get('form_values', {})
        
        # Delegate to service (exceptions are handled by custom exception handler)
        node = node_service.create_node(workflow, node_type, position, form_values)
        
        # Return using CanvasNodeSerializer for consistent format
        canvas_serializer = CanvasNodeSerializer(node, context={'request': request})
        return Response(canvas_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'], url_path='position')
    def update_position(self, request, workflow_pk=None, pk=None):
        """
        Update node position in the workflow.
        View only handles HTTP request/response, delegates to service.
        """
        node = self.get_object()
        position = request.data.get('position', {})
        
        # Delegate to service (exceptions are handled by custom exception handler)
        updated_node = node_service.update_node_position(node, position)
        
        return Response(NodeSerializer(updated_node).data)

    @action(detail=True, methods=['delete'], url_path='remove')
    def remove_node(self, request, workflow_pk=None, pk=None):
        """
        Remove a node from the workflow.
        View only handles HTTP request/response, delegates to service.
        """
        node = self.get_object()
        
        # Delegate to service (exceptions are handled by custom exception handler)
        node_service.delete_node(node)
        
        return Response({'message': 'Node removed successfully'})

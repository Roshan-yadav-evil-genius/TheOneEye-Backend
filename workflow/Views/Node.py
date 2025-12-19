from django.shortcuts import get_object_or_404
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from workflow.models import Node, WorkFlow
from workflow.Serializers import NodeSerializer, NodeCreateSerializer
from workflow.Serializers.Canvas import CanvasNodeSerializer
from workflow.services import dependency_service


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
        if self.action == 'create':
            return NodeCreateSerializer
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
        """Add a node to the workflow canvas"""
        workflow = self.get_workflow()
        
        # Get node type and position
        node_type = request.data.get('nodeTemplate', 'custom-node')
        position = request.data.get('position', {'x': 0, 'y': 0})
        
        # Prepare data for NodeCreateSerializer
        node_data = {
            'node_type': node_type,
            'x': position.get('x', 0),
            'y': position.get('y', 0),
            'form_values': request.data.get('form_values', {})
        }
        
        # Use NodeCreateSerializer
        serializer = NodeCreateSerializer(
            data=node_data, 
            context={'workflow': workflow, 'request': request}
        )
        
        if serializer.is_valid():
            node = serializer.save()
            # Return using CanvasNodeSerializer for consistent format
            canvas_serializer = CanvasNodeSerializer(node, context={'request': request})
            return Response(canvas_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'], url_path='position')
    def update_position(self, request, workflow_pk=None, pk=None):
        """Update node position in the workflow"""
        node = self.get_object()
        position = request.data.get('position', {})
        
        node.x = position.get('x', node.x)
        node.y = position.get('y', node.y)
        node.save()
        
        return Response(NodeSerializer(node).data)

    @action(detail=True, methods=['delete'], url_path='remove')
    def remove_node(self, request, workflow_pk=None, pk=None):
        """Remove a node from the workflow"""
        node = self.get_object()
        node.delete()
        return Response({'message': 'Node removed successfully'})

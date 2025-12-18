from django.shortcuts import get_object_or_404
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from workflow.models import Node, WorkFlow
from workflow.Serializers import NodeSerializer,NodeCreateSerializer

class NodeViewSet(ModelViewSet):
    serializer_class = NodeSerializer

    def get_queryset(self):
        workflow_pk = self.kwargs.get("workflow_pk")
        if workflow_pk:
            return Node.objects.filter(workflow_id = workflow_pk)
        return Node.objects.all()
    
    def perform_create(self, serializer):
        workflow_id = self.kwargs.get('workflow_pk')
        workflow = get_object_or_404(WorkFlow, id=workflow_id)
        serializer.save(workflow=workflow)
        
    def get_serializer_class(self):
        if self.action == 'create':
            return NodeCreateSerializer
        return NodeSerializer

    @action(detail=True, methods=['get'], url_path='input')
    def get_input(self, request, workflow_pk=None, pk=None):
        """Get aggregated input data from all connected source nodes"""
        node = self.get_object()
        incoming_connections = node.incoming_connections.select_related('source_node')
        input_data = {}
        for connection in incoming_connections:
            source_node_id = str(connection.source_node.id)
            input_data[source_node_id] = connection.source_node.config
        return Response(input_data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='output')
    def get_output(self, request, workflow_pk=None, pk=None):
        """Get the output data for this node"""
        node = self.get_object()
        return Response(node.config, status=status.HTTP_200_OK)

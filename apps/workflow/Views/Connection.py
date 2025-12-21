from django.shortcuts import get_object_or_404
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from apps.workflow.models import Connection, WorkFlow, Node
from apps.workflow.Serializers import ConnectionSerializer


class ConnectionViewSet(ModelViewSet):
    serializer_class = ConnectionSerializer

    def get_queryset(self):
        workflow_pk = self.kwargs.get("workflow_pk")
        if workflow_pk:
            return Connection.objects.filter(workflow_id=workflow_pk)
        return Connection.objects.all()
    
    def get_workflow(self):
        """Get the workflow from URL kwargs"""
        workflow_pk = self.kwargs.get('workflow_pk')
        return get_object_or_404(WorkFlow, id=workflow_pk)
    
    def get_serializer_context(self):
        """Add workflow context for serializers"""
        context = super().get_serializer_context()
        workflow_pk = self.kwargs.get("workflow_pk")
        if workflow_pk:
            context['workflow_id'] = workflow_pk
            context['workflow'] = self.get_workflow()
        return context
    
    def perform_create(self, serializer):
        workflow = self.get_workflow()
        serializer.save(workflow=workflow)

    @action(detail=False, methods=['post'], url_path='add')
    def add_connection(self, request, workflow_pk=None):
        """Add a connection between nodes in the workflow"""
        workflow = self.get_workflow()
        
        source_node_id = request.data.get('source')
        target_node_id = request.data.get('target')
        source_handle = request.data.get('sourceHandle', 'default')
        
        try:
            source_node = Node.objects.get(id=source_node_id, workflow=workflow)
            target_node = Node.objects.get(id=target_node_id, workflow=workflow)
        except Node.DoesNotExist:
            return Response(
                {'error': 'Source or target node not found'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if connection already exists (including source_handle)
        if Connection.objects.filter(
            workflow=workflow,
            source_node=source_node,
            target_node=target_node,
            source_handle=source_handle
        ).exists():
            return Response(
                {'error': 'Connection already exists'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        connection_data = {
            'workflow': workflow.id,
            'source_node': source_node.id,
            'target_node': target_node.id,
            'source_handle': source_handle
        }
        
        serializer = ConnectionSerializer(
            data=connection_data, 
            context={'workflow_id': workflow.id, 'workflow': workflow}
        )
        if serializer.is_valid():
            connection = serializer.save()
            return Response(ConnectionSerializer(connection).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], url_path='remove')
    def remove_connection(self, request, workflow_pk=None, pk=None):
        """Remove a connection from the workflow"""
        connection = self.get_object()
        connection.delete()
        return Response({'message': 'Connection removed successfully'})
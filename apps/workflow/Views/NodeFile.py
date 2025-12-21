from django.shortcuts import get_object_or_404
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from apps.workflow.models import NodeFile, Node, WorkFlow
from apps.workflow.Serializers import NodeFileSerializer, NodeFileUploadSerializer


class NodeFileViewSet(ModelViewSet):
    """ViewSet for managing node files"""
    serializer_class = NodeFileSerializer
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        """Get files for a specific node"""
        workflow_pk = self.kwargs.get("workflow_pk")
        node_pk = self.kwargs.get("node_pk")
        
        if workflow_pk and node_pk:
            # Verify the node belongs to the workflow
            node = get_object_or_404(Node, id=node_pk, workflow_id=workflow_pk)
            return NodeFile.objects.filter(node=node)
        return NodeFile.objects.none()
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action in ['upload', 'update_file']:
            return NodeFileUploadSerializer
        return NodeFileSerializer
    
    @action(detail=False, methods=['post'], url_path='upload')
    def upload(self, request, workflow_pk=None, node_pk=None):
        """
        Upload a file for a specific node.
        If a file with the same key exists, it will be overwritten.
        """
        # Get the node and verify it belongs to the workflow
        node = get_object_or_404(Node, id=node_pk, workflow_id=workflow_pk)
        
        # Add the node to the validated data
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Set the node in the serializer context
        serializer.validated_data['node'] = node
        
        # Create or update the file
        node_file = serializer.save()
        
        # Return the created file data
        response_serializer = NodeFileSerializer(node_file)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['put', 'patch'], url_path='update-file')
    def update_file(self, request, workflow_pk=None, node_pk=None, pk=None):
        """
        Update an existing file for a specific node.
        This will replace the existing file with a new one.
        """
        # Get the node file
        node_file = get_object_or_404(
            NodeFile, 
            id=pk, 
            node_id=node_pk, 
            node__workflow_id=workflow_pk
        )
        
        # Get the node
        node = get_object_or_404(Node, id=node_pk, workflow_id=workflow_pk)
        
        # Create serializer with the existing key
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Set the node and key in the validated data
        serializer.validated_data['node'] = node
        serializer.validated_data['key'] = node_file.key
        
        # Delete the old file and create a new one
        node_file.delete()  # This will also remove the file from filesystem
        new_node_file = serializer.save()
        
        # Return the updated file data
        response_serializer = NodeFileSerializer(new_node_file)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
    
    def destroy(self, request, workflow_pk=None, node_pk=None, pk=None):
        """
        Delete a file. This will also remove the file from the filesystem.
        """
        node_file = get_object_or_404(
            NodeFile, 
            id=pk, 
            node_id=node_pk, 
            node__workflow_id=workflow_pk
        )
        
        node_file.delete()  # This will also remove the file from filesystem
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    def list(self, request, workflow_pk=None, node_pk=None):
        """
        List all files for a specific node.
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, workflow_pk=None, node_pk=None, pk=None):
        """
        Retrieve a specific file for a node.
        """
        node_file = get_object_or_404(
            NodeFile, 
            id=pk, 
            node_id=node_pk, 
            node__workflow_id=workflow_pk
        )
        serializer = self.get_serializer(node_file)
        return Response(serializer.data)

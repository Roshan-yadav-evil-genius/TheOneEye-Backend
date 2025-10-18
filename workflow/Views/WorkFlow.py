from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework import status
from workflow.Serializers.WorkFlow import RawWorkFlawSerializer
from workflow.models import WorkFlow, Node, Connection, StandaloneNode
from workflow.Serializers import WorkFlowSerializer
from workflow.Serializers.Node import NodeSerializer, NodeCreateSerializer
from workflow.Serializers.Connection import ConnectionSerializer
from workflow.Serializers.Canvas import CanvasDataSerializer, AvailableNodeTemplateSerializer, CanvasNodeSerializer
from rest_framework.decorators import action
from celery.result import AsyncResult
from workflow.tasks import execute_workflow,stop_workflow,execute_single_node
from django.db import transaction
from django.core.serializers.json import DjangoJSONEncoder
import json


class WorkFlowViewSet(ModelViewSet):
    queryset = WorkFlow.objects.all()
    serializer_class = WorkFlowSerializer

    @action(detail=True, methods=["get"])
    def start_execution(self, request, pk=None):
        workFlowObject: WorkFlow = self.get_object()
        workFlowConfig = RawWorkFlawSerializer(workFlowObject)
        with open("workFlowConfig.json","w") as file:
            json.dump(workFlowConfig.data, file, cls=DjangoJSONEncoder)
        task:AsyncResult = execute_workflow.delay(workFlowConfig.data)
        print(f"Task: {task}, id:{task.id}")
        workFlowObject.task_id = task.id
        workFlowObject.save()
        return Response({"task_id": task.id, "status": task.status})
    
    @action(detail=True, methods=["get"])
    def stop_execution(self, request, pk=None):
        workFlowObject: WorkFlow = self.get_object()
        task:AsyncResult = stop_workflow.delay(str(workFlowObject.id))
        task.get(5)
        return Response({"task_id": task.id, "status": task.status})

    @action(detail=True, methods=["get"])
    def task_status(self, request, pk: str):
        workFlowObject: WorkFlow = self.get_object()
        task_id = workFlowObject.task_id
        print(f"Task: {task_id}")
        if not task_id:
            return Response({"error": "No task associated with this workflow"}, status=400)

        result: AsyncResult = AsyncResult(task_id)
        return Response({
            "task_id": task_id,
            "status": result.status,
        })

    @action(detail=True, methods=["get"])
    def rawconfig(self,request,pk:str):
        workFlow = WorkFlow.objects.get(id=pk)
        data = RawWorkFlawSerializer(workFlow)
        return Response(data.data)

    @action(detail=True, methods=["get"])
    def canvas_data(self, request, pk=None):
        """Get workflow canvas data with full node information"""
        workflow = self.get_object()
        serializer = CanvasDataSerializer(workflow, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def available_nodes(self, request):
        """Get available node templates that can be added to canvas"""
        standalone_nodes = StandaloneNode.objects.filter(is_active=True)
        serializer = AvailableNodeTemplateSerializer(
            standalone_nodes, 
            many=True, 
            context={'request': request}
        )
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def add_node(self, request, pk=None):
        """Add a node to the workflow canvas"""
        workflow = self.get_object()
        
        # Get node template data
        node_template_id = request.data.get('nodeTemplate', 'custom-node')
        position = request.data.get('position', {'x': 0, 'y': 0})
        
        # Try to get the StandaloneNode template if nodeTemplate is provided
        standalone_node = None
        if node_template_id and node_template_id != 'custom-node':
            try:
                standalone_node = StandaloneNode.objects.get(id=node_template_id, is_active=True)
            except StandaloneNode.DoesNotExist:
                return Response(
                    {'error': f'Node template with ID {node_template_id} not found'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Prepare data for NodeCreateSerializer
        node_data = {
            'node_type': standalone_node.id if standalone_node else None,
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

    @action(detail=True, methods=["post"])
    def add_connection(self, request, pk=None):
        """Add a connection between nodes in the workflow"""
        workflow = self.get_object()
        
        source_node_id = request.data.get('source')
        target_node_id = request.data.get('target')
        
        try:
            source_node = Node.objects.get(id=source_node_id, workflow=workflow)
            target_node = Node.objects.get(id=target_node_id, workflow=workflow)
        except Node.DoesNotExist:
            return Response(
                {'error': 'Source or target node not found'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if connection already exists
        if Connection.objects.filter(
            workflow=workflow,
            source_node=source_node,
            target_node=target_node
        ).exists():
            return Response(
                {'error': 'Connection already exists'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        connection_data = {
            'workflow': workflow.id,
            'source_node': source_node.id,
            'target_node': target_node.id
        }
        
        serializer = ConnectionSerializer(data=connection_data, context={'workflow_id': workflow.id, 'workflow': workflow})
        if serializer.is_valid():
            connection = serializer.save()
            return Response(ConnectionSerializer(connection).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["patch"])
    def update_node_position(self, request, pk=None):
        """Update node position in the workflow"""
        workflow = self.get_object()
        node_id = request.data.get('nodeId')
        position = request.data.get('position', {})
        
        try:
            node = Node.objects.get(id=node_id, workflow=workflow)
            node.x = position.get('x', node.x)
            node.y = position.get('y', node.y)
            node.save()
            return Response(NodeSerializer(node).data)
        except Node.DoesNotExist:
            return Response(
                {'error': 'Node not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=["delete"])
    def remove_node(self, request, pk=None):
        """Remove a node from the workflow"""
        workflow = self.get_object()
        node_id = request.data.get('nodeId')
        
        try:
            node = Node.objects.get(id=node_id, workflow=workflow)
            node.delete()
            return Response({'message': 'Node removed successfully'})
        except Node.DoesNotExist:
            return Response(
                {'error': 'Node not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=["delete"])
    def remove_connection(self, request, pk=None):
        """Remove a connection from the workflow"""
        workflow = self.get_object()
        connection_id = request.data.get('connectionId')
        
        try:
            connection = Connection.objects.get(id=connection_id, workflow=workflow)
            connection.delete()
            return Response({'message': 'Connection removed successfully'})
        except Connection.DoesNotExist:
            return Response(
                {'error': 'Connection not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=["post"])
    def execute_single_node(self, request, pk=None):
        """Execute a single node with its dependencies"""
        workflow = self.get_object()
        node_id = request.data.get('node_id')
        
        if not node_id:
            return Response(
                {'error': 'node_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Verify the node exists in this workflow
            node = Node.objects.get(id=node_id, workflow=workflow)
        except Node.DoesNotExist:
            return Response(
                {'error': 'Node not found in this workflow'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Start the Celery task
        task = execute_single_node.delay(str(workflow.id), str(node_id))
        print("Executing Node", str(node_id))
        
        return Response({
            "task_id": task.id, 
            "status": task.status,
            "message": f"Started execution of node {node.node_type.name if node.node_type else 'Unknown'}"
        })
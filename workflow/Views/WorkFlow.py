from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework import status
from workflow.Serializers.WorkFlow import RawWorkFlawSerializer
from workflow.models import WorkFlow, Node, Connection
from workflow.Serializers import WorkFlowSerializer
from workflow.Serializers.Node import NodeSerializer, NodeCreateSerializer
from workflow.Serializers.Connection import ConnectionSerializer
from workflow.Serializers.Canvas import CanvasDataSerializer, CanvasNodeSerializer
from rest_framework.decorators import action
from celery.result import AsyncResult
from workflow.tasks import execute_workflow, stop_workflow
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
        # with open("workFlowConfig.json","w") as file:
        #     json.dump(workFlowConfig.data, file, cls=DjangoJSONEncoder)
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

    @action(detail=True, methods=["post"])
    def add_node(self, request, pk=None):
        """Add a node to the workflow canvas"""
        workflow = self.get_object()
        
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

    @action(detail=True, methods=["post"])
    def add_connection(self, request, pk=None):
        """Add a connection between nodes in the workflow"""
        workflow = self.get_object()
        
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
    def execute_and_save_node(self, request, pk=None):
        """
        Execute a workflow node and save all execution data.
        
        Flow:
        1. Save form_values and input_data to Node model
        2. Execute the node using core engine
        3. Save output_data to Node model
        4. Return execution result
        
        Request body:
        {
            "node_id": "uuid",
            "form_values": { ... },
            "input_data": { ... }
        }
        """
        workflow = self.get_object()
        node_id = request.data.get('node_id')
        form_values = request.data.get('form_values', {})
        input_data = request.data.get('input_data', {})
        
        if not node_id:
            return Response(
                {'error': 'node_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get the workflow node instance
            node_instance = Node.objects.get(id=node_id, workflow=workflow)
        except Node.DoesNotExist:
            return Response(
                {'error': 'Node not found in this workflow'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Step 1: Save form_values and input_data
        node_instance.form_values = form_values
        node_instance.input_data = input_data
        node_instance.save()
        
        # Step 2: Execute the node using core engine
        try:
            from nodes.services import get_node_services
            services = get_node_services()
            
            # Find the node type metadata
            node_metadata = services.node_registry.find_by_identifier(node_instance.node_type)
            
            if node_metadata is None:
                return Response(
                    {'error': f'Node type not found: {node_instance.node_type}'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Execute the node
            result = services.node_executor.execute(node_metadata, input_data, form_values)
            
            # Step 3: Save output_data
            if result.get('success'):
                output = result.get('output', {})
                # Extract data from output if it's wrapped
                if isinstance(output, dict) and 'data' in output:
                    node_instance.output_data = output.get('data', {})
                else:
                    node_instance.output_data = output
                node_instance.save()
            
            # Step 4: Return the result
            return Response({
                'success': result.get('success', False),
                'node_id': str(node_instance.id),
                'node_type': node_instance.node_type,
                'input_data': input_data,
                'form_values': form_values,
                'output': result.get('output'),
                'error': result.get('error'),
                'error_type': result.get('error_type'),
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e),
                'error_type': 'ExecutionError',
                'node_id': str(node_instance.id),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

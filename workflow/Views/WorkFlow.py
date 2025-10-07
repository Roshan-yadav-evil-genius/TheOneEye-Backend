from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework import status
from workflow.Serializers.WorkFlow import RawWorkFlawSerializer
from workflow.models import WorkFlow, Node, Connection, StandaloneNode
from workflow.Serializers import WorkFlowSerializer
from workflow.Serializers.Node import NodeSerializer, NodeCreateSerializer
from workflow.Serializers.Connection import ConnectionSerializer
from rest_framework.decorators import action
from celery.result import AsyncResult
from workflow.tasks import execute_workflow,stop_workflow
from django.db import transaction


class WorkFlowViewSet(ModelViewSet):
    queryset = WorkFlow.objects.all()
    serializer_class = WorkFlowSerializer

    @action(detail=True, methods=["get"])
    def start_execution(self, request, pk=None):
        workFlowObject: WorkFlow = self.get_object()
        workFlowConfig = RawWorkFlawSerializer(workFlowObject)
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
        nodes = workflow.nodes.select_related('node_type').all()  # Include StandaloneNode data
        connections = workflow.connections.all()
        
        # Full nodes with StandaloneNode template data
        canvas_nodes = []
        for node in nodes:
            node_data = node.data or {}
            standalone_node = node.node_type  # The linked StandaloneNode template
            
            canvas_nodes.append({
                'id': str(node.id),
                'position': {'x': node.position_x, 'y': node.position_y},
                'data': {
                    # Only node-specific configuration data, no redundant fields
                    'formValues': node_data.get('formValues', {}),
                    'customSettings': node_data.get('customSettings', {}),
                },
                'form_values': node.form_values or {},
                'node_type': {
                    'id': str(standalone_node.id) if standalone_node else None,
                    'name': standalone_node.name if standalone_node else None,
                    'type': standalone_node.type if standalone_node else None,
                    'description': standalone_node.description if standalone_node else None,
                    'logo': request.build_absolute_uri(standalone_node.logo.url) if standalone_node and standalone_node.logo else None,
                    'form_configuration': standalone_node.form_configuration if standalone_node else {},
                    'tags': standalone_node.tags if standalone_node else [],
                    'node_group': {
                        'id': str(standalone_node.node_group.id) if standalone_node and standalone_node.node_group else None,
                        'name': standalone_node.node_group.name if standalone_node and standalone_node.node_group else None,
                        'description': standalone_node.node_group.description if standalone_node and standalone_node.node_group else None,
                        'icon': request.build_absolute_uri(standalone_node.node_group.icon.url) if standalone_node and standalone_node.node_group and standalone_node.node_group.icon else None,
                        'is_active': standalone_node.node_group.is_active if standalone_node and standalone_node.node_group else None,
                        'created_at': standalone_node.node_group.created_at.isoformat() if standalone_node and standalone_node.node_group else None,
                        'updated_at': standalone_node.node_group.updated_at.isoformat() if standalone_node and standalone_node.node_group else None,
                    } if standalone_node and standalone_node.node_group else None,
                    'version': standalone_node.version if standalone_node else None,
                    'is_active': standalone_node.is_active if standalone_node else None,
                    'created_by': standalone_node.created_by if standalone_node else None,
                    'created_at': standalone_node.created_at.isoformat() if standalone_node else None,
                    'updated_at': standalone_node.updated_at.isoformat() if standalone_node else None,
                } if standalone_node else None
            })
        
        # Full edges with connection data
        canvas_edges = []
        for connection in connections:
            canvas_edges.append({
                'id': str(connection.id),
                'source': str(connection.source_node.id),
                'target': str(connection.target_node.id),
                'created_at': connection.created_at.isoformat(),
            })
        
        return Response({
            'nodes': canvas_nodes,
            'edges': canvas_edges,
            'workflow': {
                'id': str(workflow.id),
                'name': workflow.name,
                'description': workflow.description,
                'status': workflow.status,
            }
        })

    @action(detail=False, methods=["get"])
    def available_nodes(self, request):
        """Get available node templates that can be added to canvas"""
        # Get available StandaloneNode templates
        standalone_nodes = StandaloneNode.objects.filter(is_active=True)
        
        node_templates = []
        for node in standalone_nodes:
            node_templates.append({
                'id': str(node.id),
                'name': node.name,
                'description': node.description or '',
                'icon': request.build_absolute_uri(node.logo.url) if node.logo else None,
                'category': node.type,
            })
        
        return Response(node_templates)

    @action(detail=True, methods=["post"])
    def add_node(self, request, pk=None):
        """Add a node to the workflow canvas"""
        workflow = self.get_object()
        
        # Get node template data
        node_template_id = request.data.get('nodeTemplate', 'custom-node')
        position = request.data.get('position', {'x': 0, 'y': 0})
        custom_data = request.data.get('data', {})
        
        # Try to get the StandaloneNode template if nodeTemplate is provided
        standalone_node = None
        if node_template_id and node_template_id != 'custom-node':
            try:
                from workflow.models import StandaloneNode
                standalone_node = StandaloneNode.objects.get(id=node_template_id, is_active=True)
            except StandaloneNode.DoesNotExist:
                return Response(
                    {'error': f'Node template with ID {node_template_id} not found'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Create node data - only store node-specific configuration, no redundant data
        node_data = {
            'formValues': custom_data.get('formValues', {}),
            'customSettings': custom_data.get('customSettings', {}),
        }
        
        # Create the node with proper StandaloneNode reference
        from workflow.models import Node
        node = Node.objects.create(
            workflow=workflow,
            node_type=standalone_node,  # Link to StandaloneNode template
            position_x=position.get('x', 0),
            position_y=position.get('y', 0),
            data=node_data
        )
        
        return Response({
            'id': str(node.id),
            'position': {'x': node.position_x, 'y': node.position_y},
            'data': node_data,
            'node_type': {
                'id': str(standalone_node.id) if standalone_node else None,
                'name': standalone_node.name if standalone_node else None,
                'type': standalone_node.type if standalone_node else None,
                'description': standalone_node.description if standalone_node else None,
                'logo': request.build_absolute_uri(standalone_node.logo.url) if standalone_node and standalone_node.logo else None,
                'form_configuration': standalone_node.form_configuration if standalone_node else {},
                'tags': standalone_node.tags if standalone_node else [],
                'node_group': {
                    'id': str(standalone_node.node_group.id) if standalone_node and standalone_node.node_group else None,
                    'name': standalone_node.node_group.name if standalone_node and standalone_node.node_group else None,
                    'description': standalone_node.node_group.description if standalone_node and standalone_node.node_group else None,
                    'icon': request.build_absolute_uri(standalone_node.node_group.icon.url) if standalone_node and standalone_node.node_group and standalone_node.node_group.icon else None,
                    'is_active': standalone_node.node_group.is_active if standalone_node and standalone_node.node_group else None,
                    'created_at': standalone_node.node_group.created_at.isoformat() if standalone_node and standalone_node.node_group else None,
                    'updated_at': standalone_node.node_group.updated_at.isoformat() if standalone_node and standalone_node.node_group else None,
                } if standalone_node and standalone_node.node_group else None,
                'version': standalone_node.version if standalone_node else None,
                'is_active': standalone_node.is_active if standalone_node else None,
                'created_by': standalone_node.created_by if standalone_node else None,
                'created_at': standalone_node.created_at.isoformat() if standalone_node else None,
                'updated_at': standalone_node.updated_at.isoformat() if standalone_node else None,
            } if standalone_node else None
        }, status=status.HTTP_201_CREATED)

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
            node.position_x = position.get('x', node.position_x)
            node.position_y = position.get('y', node.position_y)
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
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework import status
from rest_framework.decorators import action
from apps.workflow.models import WorkFlow
from apps.workflow.Serializers import WorkFlowSerializer
from apps.workflow.Serializers.WorkFlow import RawWorkFlawSerializer
from apps.workflow.Serializers.Canvas import CanvasDataSerializer
from apps.workflow.services import workflow_execution_service


class WorkFlowViewSet(ModelViewSet):
    queryset = WorkFlow.objects.all()
    serializer_class = WorkFlowSerializer

    @action(detail=True, methods=["get"])
    def start_execution(self, request, pk=None):
        """Start workflow execution"""
        workflow = self.get_object()
        workflow_config = RawWorkFlawSerializer(workflow).data
        result = workflow_execution_service.start_execution(workflow, workflow_config)
        return Response(result)
    
    @action(detail=True, methods=["get"])
    def stop_execution(self, request, pk=None):
        """Stop workflow execution"""
        workflow = self.get_object()
        result = workflow_execution_service.stop_execution(workflow)
        return Response(result)

    @action(detail=True, methods=["get"])
    def task_status(self, request, pk=None):
        """Get workflow execution task status"""
        workflow = self.get_object()
        result = workflow_execution_service.get_task_status(workflow)
        
        if result is None:
            return Response(
                {"error": "No task associated with this workflow"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(result)

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
    def execute_and_save_node(self, request, pk=None):
        """
        Execute a workflow node and save all execution data.
        
        Request body:
        {
            "node_id": "uuid",
            "form_values": { ... },
            "input_data": { ... },
            "session_id": "optional session id for stateful execution"
        }
        """
        from apps.workflow.services import node_execution_service
        
        workflow = self.get_object()
        node_id = request.data.get('node_id')
        form_values = request.data.get('form_values', {})
        input_data = request.data.get('input_data', {})
        session_id = request.data.get('session_id')
        
        if not node_id:
            return Response(
                {'error': 'node_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the node instance
        node = node_execution_service.get_node_for_execution(workflow.id, node_id)
        if node is None:
            return Response(
                {'error': 'Node not found in this workflow'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Execute the node using the service with session support
        result = node_execution_service.execute_node(node, form_values, input_data, session_id)
        
        # Return appropriate response based on result
        if result.get('error_type') == 'NodeTypeNotFound':
            return Response(result, status=status.HTTP_404_NOT_FOUND)
        elif not result.get('success'):
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(result)

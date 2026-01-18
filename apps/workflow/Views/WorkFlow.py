from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
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
        from django.db.models import F
        from django.utils import timezone
        
        workflow = self.get_object()
        
        # Update metrics synchronously before starting task
        now = timezone.now()
        WorkFlow.objects.filter(id=workflow.id).update(
            last_run=now,
            runs_count=F('runs_count') + 1
        )
        
        # Refresh workflow object to get updated values (critical - prevents overwriting the update)
        workflow.refresh_from_db()
        
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
        View only handles HTTP request/response, delegates to service.
        
        Request body:
        {
            "node_id": "uuid",
            "form_values": { ... },
            "input_data": { ... },
            "session_id": "optional session id for stateful execution",
            "timeout": 300  // optional timeout in seconds (default: 300)
        }
        """
        from apps.workflow.services import node_execution_service
        
        workflow = self.get_object()
        node_id = request.data.get('node_id')
        form_values = request.data.get('form_values', {})
        input_data = request.data.get('input_data', {})
        session_id = request.data.get('session_id')
        timeout = request.data.get('timeout', 300)  # Default 300 seconds (5 minutes)
        
        # Delegate to service - handles all validation and execution
        # Exceptions are handled by custom exception handler
        result = node_execution_service.execute_and_save_node(
            str(workflow.id),
            node_id,
            form_values,
            input_data,
            session_id,
            timeout
        )
        
        return Response(result, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], authentication_classes=[], permission_classes=[AllowAny])
    def execute(self, request, pk=None):
        """
        Execute an API workflow synchronously (Public endpoint - no authentication required).
        
        This endpoint is for API workflows only. It executes the workflow
        from start to finish and returns the output from the last node.
        
        The workflow must:
        - Be of type 'api' (workflow_type == 'api')
        - Start with a WebhookProducer node
        
        Request body:
        {
            "input": { ... },  // Input data to pass to the workflow
            "timeout": 300     // Optional timeout in seconds (default: 300)
        }
        
        Response (success):
        {
            "success": true,
            "workflow_id": "uuid",
            "output": { ... },  // Output from the last executed node
            "execution_time_ms": 523
        }
        
        Response (error):
        {
            "success": false,
            "error": "Error message",
            "workflow_id": "uuid",
            "execution_time_ms": 100
        }
        """
        from apps.workflow.services import api_execution_service
        
        workflow = self.get_object()
        input_data = request.data.get('input', {})
        timeout = request.data.get('timeout', 300)  # Default 300 seconds (5 minutes)
        
        # Capture request context (headers, query params, method) for webhook node
        request_context = {
            'headers': dict(request.headers),
            'query_params': dict(request.query_params),
            'method': request.method
        }
        
        # Delegate to service - handles validation and execution
        result = api_execution_service.execute_workflow(
            str(workflow.id),
            input_data,
            timeout,
            request_context=request_context
        )
        
        # Return appropriate status code based on success
        status_code = status.HTTP_200_OK if result.get('success') else status.HTTP_400_BAD_REQUEST
        return Response(result, status=status_code)

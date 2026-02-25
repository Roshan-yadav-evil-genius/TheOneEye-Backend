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

    @action(detail=True, methods=["get"], authentication_classes=[], permission_classes=[AllowAny])
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
    
    @action(detail=True, methods=["get"], authentication_classes=[], permission_classes=[AllowAny])
    def stop_execution(self, request, pk=None):
        """Stop workflow execution"""
        workflow = self.get_object()
        result = workflow_execution_service.stop_execution(workflow)
        return Response(result)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        """
        Activate an API workflow (mark as ready to receive requests).
        
        This endpoint is for API workflows only. When activated, the workflow
        will accept requests via the /execute/ endpoint.
        
        Note: This does NOT start a Celery task or WebSocket connection.
        It simply marks the workflow as 'active'.
        """
        workflow = self.get_object()
        
        if workflow.workflow_type != 'api':
            return Response(
                {"error": "Only API workflows can be activated via this endpoint. Use start_execution for production workflows."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        workflow.status = 'active'
        workflow.save()
        
        return Response({
            "status": "active",
            "message": f"Workflow '{workflow.name}' is now accepting requests via /execute/"
        })

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        """
        Deactivate an API workflow (stop accepting requests).
        
        This endpoint is for API workflows only. When deactivated, the workflow
        will reject requests via the /execute/ endpoint.
        """
        workflow = self.get_object()
        
        if workflow.workflow_type != 'api':
            return Response(
                {"error": "Only API workflows can be deactivated via this endpoint. Use stop_execution for production workflows."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        workflow.status = 'inactive'
        workflow.save()
        
        return Response({
            "status": "inactive",
            "message": f"Workflow '{workflow.name}' is no longer accepting requests"
        })

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        """Duplicate a workflow with all its nodes and connections"""
        from apps.workflow.models import Node, Connection
        
        workflow = self.get_object()
        
        # Create new workflow copy
        new_workflow = WorkFlow.objects.create(
            name=f"{workflow.name} (Copy)",
            description=workflow.description,
            category=workflow.category,
            workflow_type=workflow.workflow_type,
            status='inactive',
            tags=workflow.tags.copy() if workflow.tags else [],
        )
        
        # Copy nodes and build ID mapping
        node_mapping = {}
        for node in workflow.nodes.all():
            new_node = Node.objects.create(
                workflow=new_workflow,
                node_type=node.node_type,
                x=node.x,
                y=node.y,
                form_values=node.form_values.copy() if node.form_values else {},
                config=node.config.copy() if node.config else {},
            )
            node_mapping[str(node.id)] = new_node
        
        # Copy connections with remapped node references
        for conn in workflow.connections.all():
            Connection.objects.create(
                workflow=new_workflow,
                source_node=node_mapping[str(conn.source_node.id)],
                target_node=node_mapping[str(conn.target_node.id)],
                source_handle=conn.source_handle,
            )
        
        return Response(WorkFlowSerializer(new_workflow).data, status=status.HTTP_201_CREATED)

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

    @action(detail=True, methods=["post"])
    def execute_for_each_iteration(self, request, pk=None):
        """
        Run one iteration of a ForEach node (iterate and stop).
        Request body: node_id, form_values, input_data, optional iteration_index, optional timeout.
        If iteration_index omitted, backend derives next index from node.output_data.forEachNode.state.
        Persists forEachNode state to Node.output_data on success.
        """
        from apps.workflow.services import for_each_iteration_service
        from apps.workflow.services.node_execution_service import NodeExecutionService

        workflow = self.get_object()
        node_id = request.data.get("node_id")
        form_values = request.data.get("form_values", {})
        input_data = request.data.get("input_data", {})
        iteration_index = request.data.get("iteration_index")  # None if omitted; backend derives from state
        timeout = request.data.get("timeout")

        if not node_id:
            return Response(
                {"success": False, "error": "node_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = for_each_iteration_service.execute_for_each_iteration(
            workflow_id=str(workflow.id),
            node_id=node_id,
            form_values=form_values,
            input_data=input_data,
            iteration_index=iteration_index,
            timeout=timeout,
        )

        if result.get("success") and result.get("output", {}).get("data"):
            try:
                node = NodeExecutionService.get_node_for_execution(str(workflow.id), node_id)
                node.output_data = result["output"]["data"]
                node.save()
            except Exception:
                pass

        return Response(result, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def clear_node_output(self, request, pk=None):
        """
        Clear a node's output_data in the DB (e.g. on Reset so iterate-and-stop starts fresh).
        Request body: node_id.
        """
        from apps.workflow.services.node_execution_service import NodeExecutionService

        workflow = self.get_object()
        node_id = request.data.get("node_id")
        if not node_id:
            return Response(
                {"success": False, "error": "node_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            node = NodeExecutionService.get_node_for_execution(str(workflow.id), node_id)
            node.output_data = {}
            node.save()
            return Response({"success": True}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

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

from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from workflow.Serializers.WorkFlow import RawWorkFlawSerializer
from workflow.models import WorkFlow
from workflow.Serializers import WorkFlowSerializer
from rest_framework.decorators import action
from celery.result import AsyncResult
from workflow.tasks import execute_workflow


class WorkFlowViewSet(ModelViewSet):
    queryset = WorkFlow.objects.all()
    serializer_class = WorkFlowSerializer

    @action(detail=True, methods=["get"])
    def execute(self, request, pk=None):
        workFlowObject: WorkFlow = self.get_object()
        workFlowConfig = RawWorkFlawSerializer(workFlowObject)
        task:AsyncResult = execute_workflow.delay(workFlowConfig.data)
        workFlowObject.task_id = task.id
        workFlowObject.save()
        return Response({"task_id": task.id, "status": task.status})

    @action(detail=True, methods=["get"])
    def task_status(self, request, pk: str):
        workFlowObject: WorkFlow = self.get_object()
        task_id = workFlowObject.task_id

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
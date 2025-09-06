from django.shortcuts import get_object_or_404
from rest_framework.viewsets import ModelViewSet
from workflow.models import Connection, WorkFlow
from workflow.Serializers import ConnectionSerializer


class ConnectionViewSet(ModelViewSet):
    serializer_class = ConnectionSerializer

    def get_queryset(self):
        workflow_pk = self.kwargs.get("workflow_pk")
        if workflow_pk:
            return Connection.objects.filter(workflow_id = workflow_pk)
        return Connection.objects.all()
    
    def get_serializer_context(self): # get_serializer_context() is a DRF ViewSet method that lets you pass extra context to your serializers.
        context = super().get_serializer_context()
        workflow_pk = self.kwargs.get("workflow_pk")
        if workflow_pk:
            context['workflow_id'] = workflow_pk
        return context
    
    def perform_create(self, serializer):
        workflow_id = self.kwargs.get('workflow_pk')
        workflow = get_object_or_404(WorkFlow, id=workflow_id)
        serializer.save(workflow=workflow)
from django.shortcuts import get_object_or_404
from rest_framework.viewsets import ModelViewSet
from workflow.models import Node, WorkFlow
from workflow.Serializers import NodeSerializer,NodeCreateSerializer

class NodeViewSet(ModelViewSet):
    serializer_class = NodeSerializer

    def get_queryset(self):
        workflow_pk = self.kwargs.get("workflow_pk")
        if workflow_pk:
            return Node.objects.filter(workflow_id = workflow_pk)
        return Node.objects.all()
    
    def perform_create(self, serializer):
        workflow_id = self.kwargs.get('workflow_pk')
        workflow = get_object_or_404(WorkFlow, id=workflow_id)
        serializer.save(workflow=workflow)
        
    def get_serializer_class(self):
        if self.action == 'create':
            return NodeCreateSerializer
        return NodeSerializer
    
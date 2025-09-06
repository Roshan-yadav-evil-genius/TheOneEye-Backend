from rest_framework.viewsets import ModelViewSet
from workflow.models import WorkFlow
from workflow.Serializers import WorkFlowSerializer


class WorkFlowViewSet(ModelViewSet):
    queryset = WorkFlow.objects.all()
    serializer_class = WorkFlowSerializer

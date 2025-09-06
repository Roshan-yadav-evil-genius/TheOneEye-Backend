from rest_framework.viewsets import ModelViewSet
from workflow.models import NodeType
from workflow.Serializers import NodeTypeSerializer

class NodeTypeViewSet(ModelViewSet):
    queryset=NodeType.objects.all()
    serializer_class = NodeTypeSerializer

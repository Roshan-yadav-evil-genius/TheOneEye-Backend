from workflow.models import NodeType
from rest_framework.serializers import ModelSerializer

class NodeTypeSerializer(ModelSerializer):
    class Meta:
        model = NodeType
        fields = ["id", "name", "description","initiator"]
        read_only_fields = ["id", "created_at", "updated_at"]
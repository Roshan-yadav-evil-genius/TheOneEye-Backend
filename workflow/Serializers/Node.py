from workflow.models import Node,NodeType
from .NodeType import NodeTypeSerializer
from rest_framework.serializers import ModelSerializer,JSONField


class NodeSerializer(ModelSerializer):
    node_type = NodeTypeSerializer(read_only=True)

    class Meta:
        model = Node
        exclude = ["workflow"]
        read_only_fields = ["id", "created_at", "updated_at"]


class NodeCreateSerializer(ModelSerializer):
    data = JSONField(default=dict)
    class Meta:
        model = Node
        fields = ['id', 'node_type', 'position_x', 'position_y', 'data']
    

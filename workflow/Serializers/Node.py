from workflow.models import Node,NodeType
from .NodeType import NodeTypeSerializer
from rest_framework.serializers import ModelSerializer,CharField,ValidationError


class NodeSerializer(ModelSerializer):
    node_type = NodeTypeSerializer(read_only=True)

    class Meta:
        model = Node
        exclude = ["workflow"]
        read_only_fields = ["id", "created_at", "updated_at"]


class NodeCreateSerializer(ModelSerializer):
    node_type = CharField()  # Accept node_type as a string key
    
    class Meta:
        model = Node
        fields = ['node_type', 'position_x', 'position_y', 'data']
    
    def validate_node_type(self, value):
        """Validate that the node_type key exists"""
        try:
            node_type = NodeType.objects.get(key=value)
            return node_type
        except NodeType.DoesNotExist:
            raise ValidationError(f"NodeType with key '{value}' does not exist")

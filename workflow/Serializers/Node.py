from workflow.models import Node, StandaloneNode
from .StandaloneNode import StandaloneNodeSerializer
from rest_framework.serializers import ModelSerializer,JSONField


class NodeSerializer(ModelSerializer):
    node_type = StandaloneNodeSerializer(read_only=True)

    class Meta:
        model = Node
        exclude = ["workflow"]
        read_only_fields = ["id", "created_at", "updated_at"]


class NodeCreateSerializer(ModelSerializer):
    class Meta:
        model = Node
        fields = ['id', 'node_type', 'position_x', 'position_y', 'data', 'form_values']
        read_only_fields = ['id']
    
    def create(self, validated_data):
        # Get workflow from context
        workflow = self.context.get('workflow')
        if workflow:
            validated_data['workflow'] = workflow
        return super().create(validated_data)
    
    def to_representation(self, instance):
        # Return the full format with nested node_type after creation
        return NodeSerializer(instance).data

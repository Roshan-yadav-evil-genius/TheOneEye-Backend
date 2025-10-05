from rest_framework.serializers import ModelSerializer, ImageField, JSONField
from workflow.models import NodeGroup


class NodeGroupSerializer(ModelSerializer):
    class Meta:
        model = NodeGroup
        fields = [
            'id', 'name', 'description', 'icon', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class NodeGroupCreateSerializer(ModelSerializer):
    # Custom fields to handle JSON parsing from FormData
    icon = ImageField(required=False, allow_null=True)
    
    class Meta:
        model = NodeGroup
        fields = [
            'name', 'description', 'icon', 'is_active'
        ]
    
    def to_representation(self, instance):
        # Return the full format after creation
        return NodeGroupSerializer(instance).data


class NodeGroupUpdateSerializer(ModelSerializer):
    # Custom fields to handle JSON parsing from FormData
    icon = ImageField(required=False, allow_null=True)
    
    class Meta:
        model = NodeGroup
        fields = [
            'name', 'description', 'icon', 'is_active'
        ]
    
    def to_representation(self, instance):
        # Return the full format after update
        return NodeGroupSerializer(instance).data

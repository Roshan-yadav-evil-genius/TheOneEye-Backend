from rest_framework import serializers
from rest_framework.serializers import ModelSerializer, ImageField, JSONField
from workflow.models import StandaloneNode
from .NodeGroup import NodeGroupSerializer

class StandaloneNodeSerializer(ModelSerializer):
    # Include node_group information in the response
    # node_group_name = serializers.CharField(source='node_group.name', read_only=True)
    # node_group_icon = serializers.ImageField(source='node_group.icon', read_only=True)
    node_group = NodeGroupSerializer()
    
    class Meta:
        model = StandaloneNode
        fields = [
            'id', 'name', 'type', 'node_group',
            'description', 'version', 'is_active', 'created_by', 'form_configuration', 'tags', 'logo',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class StandaloneNodeCreateSerializer(ModelSerializer):
    # Custom fields to handle JSON parsing from FormData
    form_configuration = JSONField(required=False, allow_null=True)
    tags = JSONField(required=False, allow_null=True)
    
    class Meta:
        model = StandaloneNode
        fields = [
            'name', 'type', 'node_group', 'description', 'version',
            'is_active', 'created_by', 'form_configuration', 'tags', 'logo'
        ]
    
    def to_representation(self, instance):
        # Return the full format after creation
        return StandaloneNodeSerializer(instance).data


class StandaloneNodeUpdateSerializer(ModelSerializer):
    # Custom fields to handle JSON parsing from FormData
    form_configuration = JSONField(required=False, allow_null=True)
    tags = JSONField(required=False, allow_null=True)
    
    class Meta:
        model = StandaloneNode
        fields = [
            'name', 'type', 'node_group', 'description', 'version',
            'is_active', 'created_by', 'form_configuration', 'tags', 'logo'
        ]
        
    def update(self, instance, validated_data):
        # Print raw request data (before saving)
        print("\n=== PUT Request Data (validated_data) ===")
        print(validated_data)
        print("========================================\n")

        # Proceed with normal update
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        # Return the full format after update
        return StandaloneNodeSerializer(instance).data

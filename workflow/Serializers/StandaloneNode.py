from rest_framework.serializers import ModelSerializer, ImageField, JSONField
from workflow.models import StandaloneNode


class StandaloneNodeSerializer(ModelSerializer):
    class Meta:
        model = StandaloneNode
        fields = [
            'id', 'name', 'type', 'category', 'description', 'version',
            'is_active', 'created_by', 'form_configuration', 'tags', 'logo',
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
            'name', 'type', 'category', 'description', 'version',
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
            'name', 'type', 'category', 'description', 'version',
            'is_active', 'created_by', 'form_configuration', 'tags', 'logo'
        ]
    
    def to_representation(self, instance):
        # Return the full format after update
        return StandaloneNodeSerializer(instance).data

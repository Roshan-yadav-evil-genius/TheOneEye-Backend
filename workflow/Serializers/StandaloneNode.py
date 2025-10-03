from rest_framework.serializers import ModelSerializer, ImageField
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
    class Meta:
        model = StandaloneNode
        fields = [
            'name', 'type', 'category', 'description', 'version',
            'is_active', 'created_by', 'form_configuration', 'tags', 'logo'
        ]
    
    def to_representation(self, instance):
        # Return the full format after creation
        return StandaloneNodeSerializer(instance).data

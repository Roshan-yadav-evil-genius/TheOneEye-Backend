from rest_framework import serializers
from apps.browsersession.models import BrowserSession

class BrowserSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrowserSession
        fields = [
            'id', 'name', 'description', 'browser_type', 
            'playwright_config', 'status', 'created_by', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class BrowserSessionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrowserSession
        fields = [
            'name', 'description', 'browser_type', 
            'playwright_config', 'status', 'created_by'
        ]
    
    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Name is required")
        return value.strip()
    
    def validate_description(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Description is required")
        return value.strip()

class BrowserSessionUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrowserSession
        fields = [
            'id', 'name', 'description', 'browser_type', 
            'playwright_config', 'status', 'created_by',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']
    
    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Name is required")
        return value.strip()
    
    def validate_description(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Description is required")
        return value.strip()


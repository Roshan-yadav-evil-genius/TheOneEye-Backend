from rest_framework import serializers
from apps.browsersession.models import BrowserSession, DomainThrottleRule

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


class DomainThrottleRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DomainThrottleRule
        fields = ["id", "session", "domain", "delay_seconds", "created_at", "updated_at"]
        read_only_fields = ["id", "session", "created_at", "updated_at"]

    def validate_domain(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Domain is required")
        return value.strip().lower()

    def validate_delay_seconds(self, value):
        if value is None or value < 0:
            raise serializers.ValidationError("Delay must be >= 0")
        return value


class DomainThrottleRuleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DomainThrottleRule
        fields = ["domain", "delay_seconds"]

    def validate_domain(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Domain is required")
        return value.strip().lower()

    def validate_delay_seconds(self, value):
        if value is None or value < 0:
            raise serializers.ValidationError("Delay must be >= 0")
        return value


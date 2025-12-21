from rest_framework import serializers
from apps.workflow.models import DemoRequest

class DemoRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DemoRequest
        fields = ['id', 'full_name', 'company_name', 'work_email', 'automation_needs', 'status', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'status', 'notes', 'created_at', 'updated_at']

class DemoRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DemoRequest
        fields = ['full_name', 'company_name', 'work_email', 'automation_needs']

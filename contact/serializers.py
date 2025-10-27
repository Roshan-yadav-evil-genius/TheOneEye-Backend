from rest_framework import serializers
from .models import ContactSubmission

class ContactSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactSubmission
        fields = ['id', 'name', 'company', 'phone', 'email', 'subject', 'message', 'created_at', 'status']
        read_only_fields = ['id', 'created_at', 'status']

class ContactSubmissionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactSubmission
        fields = ['name', 'company', 'phone', 'email', 'subject', 'message']

from rest_framework import serializers
from workflow.models import NodeFile


class NodeFileSerializer(serializers.ModelSerializer):
    """Serializer for NodeFile model"""
    
    class Meta:
        model = NodeFile
        fields = ['id', 'node', 'key', 'file', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class NodeFileUploadSerializer(serializers.ModelSerializer):
    """Serializer for file upload operations"""
    file = serializers.FileField()
    key = serializers.CharField(max_length=255)
    
    class Meta:
        model = NodeFile
        fields = ['key', 'file']
    
    def validate_file(self, value):
        """Validate uploaded file"""
        # You can add file size limits, type restrictions, etc. here
        if value.size > 100 * 1024 * 1024:  # 100MB limit
            raise serializers.ValidationError("File size cannot exceed 100MB")
        return value
    
    def create(self, validated_data):
        """Create or update NodeFile instance"""
        node = validated_data['node']
        key = validated_data['key']
        file = validated_data['file']
        
        # Check if a file with the same key already exists for this node
        existing_file = NodeFile.objects.filter(node=node, key=key).first()
        
        if existing_file:
            # Delete the existing file (this will also remove the file from filesystem)
            existing_file.delete()
        
        # Create new file instance
        node_file = NodeFile.objects.create(
            node=node,
            key=key,
            file=file
        )
        
        return node_file

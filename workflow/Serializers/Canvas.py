from rest_framework.serializers import ModelSerializer, SerializerMethodField
from .Node import NodeSerializer
from .Connection import ConnectionSerializer
from .WorkFlow import WorkFlowSerializer
from workflow.models import WorkFlow


class CanvasNodeSerializer(NodeSerializer):
    """Extended Node serializer for canvas display with position data"""
    position = SerializerMethodField()
    
    class Meta(NodeSerializer.Meta):
        exclude = ["workflow"]
        read_only_fields = ["id", "created_at", "updated_at"]
    
    def get_position(self, obj):
        return {'x': obj.x, 'y': obj.y}


class CanvasEdgeSerializer(ConnectionSerializer):
    """Extended Connection serializer for canvas display"""
    source_node = SerializerMethodField()
    target_node = SerializerMethodField()
    
    class Meta(ConnectionSerializer.Meta):
        fields = ['id', 'source_node', 'target_node', 'created_at']
    
    def get_source_node(self, obj):
        return str(obj.source_node.id)
    
    def get_target_node(self, obj):
        return str(obj.target_node.id)


class CanvasDataSerializer(ModelSerializer):
    """Complete canvas data serializer"""
    nodes = CanvasNodeSerializer(many=True, read_only=True)
    edges = CanvasEdgeSerializer(source='connections', many=True, read_only=True)
    workflow = SerializerMethodField()
    
    class Meta:
        model = WorkFlow
        fields = ['nodes', 'edges', 'workflow']
    
    def get_workflow(self, obj):
        return {
            'id': str(obj.id),
            'name': obj.name,
            'description': obj.description,
            'status': obj.status,
        }

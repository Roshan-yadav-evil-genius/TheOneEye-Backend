from workflow.Serializers.Connection import ConnectionSerializer
from workflow.Serializers.Node import NodeSerializer
from workflow.models import WorkFlow
from rest_framework.serializers import ModelSerializer

class WorkFlowSerializer(ModelSerializer):
    class Meta:
        model = WorkFlow
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "task_id"]

class RawWorkFlawSerializer(ModelSerializer):
    nodes = NodeSerializer(many=True, read_only=True)
    connections = ConnectionSerializer(many=True, read_only=True)
    class Meta:
        model = WorkFlow
        fields = "__all__"
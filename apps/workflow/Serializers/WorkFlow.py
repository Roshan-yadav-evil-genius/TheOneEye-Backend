from apps.workflow.Serializers.Connection import ConnectionSerializer
from apps.workflow.Serializers.Node import NodeSerializer
from apps.workflow.models import WorkFlow
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer


class WorkFlowSerializer(ModelSerializer):
    created_by_username = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = WorkFlow
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "updated_at", "task_id"]

    def get_created_by_username(self, obj):
        return obj.created_by.username if obj.created_by else None

class RawWorkFlawSerializer(ModelSerializer):
    nodes = NodeSerializer(many=True, read_only=True)
    connections = ConnectionSerializer(many=True, read_only=True)
    class Meta:
        model = WorkFlow
        fields = "__all__"
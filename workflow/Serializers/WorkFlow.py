from workflow.models import WorkFlow
from rest_framework.serializers import ModelSerializer

class WorkFlowSerializer(ModelSerializer):
    class Meta:
        model = WorkFlow
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "task_id"]

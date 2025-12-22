from apps.workflow.Serializers.Connection import ConnectionSerializer
from apps.workflow.Serializers.Node import NodeSerializer
from apps.workflow.models import WorkFlow
from rest_framework.serializers import ModelSerializer

class WorkFlowSerializer(ModelSerializer):
    class Meta:
        model = WorkFlow
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "task_id"]
    
    def to_representation(self, instance):
        # #region agent log
        import json
        from django.utils import timezone
        with open('/home/roshan/main/TheOneEye/Attempt3/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"location":"WorkFlow.py:12","message":"Serializer to_representation","data":{"workflow_id":str(instance.id),"last_run":str(instance.last_run) if instance.last_run else None,"runs_count":instance.runs_count,"status":instance.status,"hypothesisId":"B"},"timestamp":int(timezone.now().timestamp()*1000),"sessionId":"debug-session","runId":"run1"})+"\n")
        # #endregion
        data = super().to_representation(instance)
        # #region agent log
        with open('/home/roshan/main/TheOneEye/Attempt3/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"location":"WorkFlow.py:16","message":"Serializer data after to_representation","data":{"workflow_id":str(instance.id),"last_run_in_data":data.get("last_run"),"runs_count_in_data":data.get("runs_count"),"hypothesisId":"B"},"timestamp":int(timezone.now().timestamp()*1000),"sessionId":"debug-session","runId":"run1"})+"\n")
        # #endregion
        return data

class RawWorkFlawSerializer(ModelSerializer):
    nodes = NodeSerializer(many=True, read_only=True)
    connections = ConnectionSerializer(many=True, read_only=True)
    class Meta:
        model = WorkFlow
        fields = "__all__"
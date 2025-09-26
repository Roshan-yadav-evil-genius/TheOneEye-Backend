from workflow.models import NodeType
from rest_framework.serializers import ModelSerializer

class NodeTypeSerializer(ModelSerializer):
    # logo = SerializerMethodField()   # <-- override logo
    
    class Meta:
        model = NodeType
        fields = ["id", "name", "description","logo","input","output"]
        read_only_fields = ["id", "created_at", "updated_at"]
    
    # def get_logo(self, obj):
    #     print(obj.logo)
    #     if obj.logo:
    #         return obj.logo.url
    #     return None  # or return a default image URL
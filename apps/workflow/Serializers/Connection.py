from rest_framework.serializers import ModelSerializer, PrimaryKeyRelatedField, ValidationError
from apps.workflow.models import Connection, Node




class ConnectionSerializer(ModelSerializer):
    source_node = PrimaryKeyRelatedField(queryset=Node.objects.none())
    target_node = PrimaryKeyRelatedField(queryset=Node.objects.none())
    
    class Meta:
        model = Connection
        fields = ["id", 'source_node', 'target_node', 'source_handle']
        read_only_fields = ["id", "created_at", "updated_at"]
    
    def create(self, validated_data):
        # Get workflow from context
        workflow = self.context.get('workflow')
        if workflow:
            validated_data['workflow'] = workflow
        return super().create(validated_data)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Get workflow_id from context (passed from view)
        workflow_id = self.context.get('workflow_id')
        if workflow_id:
            # Filter nodes to only show those from the specific workflow
            workflow_nodes = Node.objects.filter(workflow_id=workflow_id)
            self.fields['source_node'].queryset = workflow_nodes
            self.fields['target_node'].queryset = workflow_nodes
    
    def validate(self, data):
        """
        Validate the connection data
        """
        source_node = data.get('source_node')
        target_node = data.get('target_node')
        
        # Check if source and target nodes are the same
        if source_node and target_node and source_node == target_node:
            raise ValidationError({
                'target_node': 'Source node and target node cannot be the same.'
            })
        
        
        return data
    


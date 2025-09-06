from rest_framework.serializers import ModelSerializer, PrimaryKeyRelatedField, ValidationError
from workflow.models import Connection, Node




class ConnectionSerializer(ModelSerializer):
    source_node = PrimaryKeyRelatedField(queryset=Node.objects.none())
    target_node = PrimaryKeyRelatedField(queryset=Node.objects.none())
    
    class Meta:
        model = Connection
        fields = ["id", 'source_node', 'target_node']
        read_only_fields = ["id", "created_at", "updated_at"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Get workflow_id from context (passed from view)
        workflow_id = self.context.get('workflow_id')
        if workflow_id:
            # Filter nodes to only show those from the specific workflow
            workflow_nodes = Node.objects.filter(workflow_id=workflow_id)
            self.fields['source_node'].queryset = workflow_nodes
            
            # Target node cannot be an initiator node
            non_initiator_nodes = workflow_nodes.filter(node_type__initiator=False)
            self.fields['target_node'].queryset = non_initiator_nodes
    
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
        
        
        # Check if target node is an initiator (should not be allowed)
        if target_node and target_node.node_type.initiator:
            raise ValidationError({
                'target_node': 'Target node cannot be an initiator node.'
            })
        
        return data
    


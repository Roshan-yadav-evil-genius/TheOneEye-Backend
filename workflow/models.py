from django.db.models import BooleanField, Model, UUIDField, CharField, TextField, DateTimeField, FloatField, JSONField, ForeignKey, CASCADE, CheckConstraint, Q, F
from django.core.exceptions import ValidationError
import uuid

class BaseModel(Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    class Meta:
        abstract = True
        ordering = ["-created_at"]



class WorkFlow(BaseModel):
    """Model to represent a workflow containing multiple nodes"""
    name = CharField(max_length=20)
    description = CharField(max_length=255, blank=True, null=True)
    task_id = CharField(max_length=255, blank=True, null=True)  # Store Celery task ID

    def __str__(self):
        return f"{self.name}({self.id})"


class NodeType(BaseModel):
    """Model to represent types of nodes, allowing dynamic creation."""
    name = CharField(max_length=100)
    module_path = CharField(max_length=50, unique=True)
    description = TextField(blank=True, null=True)

    initiator = BooleanField(default=False)
    

    def __str__(self):
        return self.name


class Node(BaseModel):
    """Model to represent individual nodes in a workflow"""
    workflow = ForeignKey(WorkFlow, on_delete=CASCADE, related_name='nodes')
    node_type = ForeignKey(NodeType, on_delete=CASCADE, related_name='nodes')

    position_x = FloatField(default=0)
    position_y = FloatField(default=0)

    data = JSONField(default=dict)  # Store node-specific data



class Connection(BaseModel):
    """Model to represent connections between nodes"""
    workflow = ForeignKey(WorkFlow, on_delete=CASCADE, related_name='connections')

    source_node = ForeignKey(Node, on_delete=CASCADE, related_name='outgoing_connections')
    target_node = ForeignKey(Node, on_delete=CASCADE, related_name='incoming_connections')
    
    class Meta:
        unique_together = ['source_node', 'target_node']

from django.db.models import BooleanField, ImageField, Model, JSONField, UUIDField, CharField, TextField, DateTimeField, FloatField, ForeignKey, CASCADE, CheckConstraint, Q, F, FileField, Index
from django.core.exceptions import ValidationError
import uuid
import os

class BaseModel(Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    class Meta:
        abstract = True
        ordering = ["-created_at"]



class WorkFlow(BaseModel):
    """Model to represent a workflow containing multiple nodes"""
    name = CharField(max_length=100)
    description = CharField(max_length=255, blank=True, null=True)
    category = CharField(max_length=50, blank=True, null=True)
    status = CharField(max_length=20, choices=[
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('error', 'Error'),
    ], default='inactive')
    last_run = DateTimeField(blank=True, null=True)
    next_run = DateTimeField(blank=True, null=True)
    runs_count = FloatField(default=0)
    success_rate = FloatField(default=0)
    tags = JSONField(default=list)
    created_by = CharField(max_length=100, blank=True, null=True)
    task_id = CharField(max_length=255, blank=True, null=True)  # Store Celery task ID

    def __str__(self):
        return f"{self.name}({self.id})"




class Node(BaseModel):
    """Model to represent individual nodes in a workflow"""
    workflow = ForeignKey(WorkFlow, on_delete=CASCADE, related_name='nodes')
    node_type = ForeignKey("StandaloneNode", on_delete=CASCADE, related_name='workflow_nodes', null=True, blank=True)

    x = FloatField(default=0)
    y = FloatField(default=0)

    form_values = JSONField(default=dict,blank=True)  # Store node-specific data node.form_configuration values
    output = JSONField(default=dict,blank=True)  # Store node execution results

    def __str__(self):
        node_name = self.node_type.name if self.node_type else f'Node {str(self.id)[:8]}'
        return f"{node_name}({self.id})"

class Connection(BaseModel):
    """Model to represent connections between nodes"""
    workflow = ForeignKey(WorkFlow, on_delete=CASCADE, related_name='connections')

    source_node = ForeignKey(Node, on_delete=CASCADE, related_name='outgoing_connections')
    target_node = ForeignKey(Node, on_delete=CASCADE, related_name='incoming_connections')
    
    class Meta:
        unique_together = ['source_node', 'target_node']


def node_file_upload_path(instance, filename):
    """Generate upload path for node files"""
    return f"node_files/{instance.node_type.id}/{instance.key}/{filename}"


class NodeGroup(BaseModel):
    """Model to represent node groups with icons for better organization"""
    name = CharField(max_length=100)
    description = TextField(blank=True, null=True)
    icon = ImageField(upload_to="node_group_icons", blank=True, null=True)
    is_active = BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class StandaloneNode(BaseModel):
    """Model to represent standalone nodes for frontend compatibility"""
    name = CharField(max_length=100)
    type = CharField(max_length=20, choices=[
        ('trigger', 'Trigger'),
        ('action', 'Action'),
        ('logic', 'Logic'),
        ('system', 'System'),
    ])
    node_group = ForeignKey(NodeGroup, on_delete=CASCADE, related_name='nodes')
    description = TextField(blank=True, null=True)
    version = CharField(max_length=20, default="1.0.0")
    is_active = BooleanField(default=True)
    created_by = CharField(max_length=100, blank=True, null=True)
    form_configuration = JSONField(default=dict)
    tags = JSONField(default=list)
    logo = ImageField(upload_to="node_logos", blank=True, null=True)

    def __str__(self):
        return f"{self.name}({self.id})"

    class Meta:
        ordering = ["-created_at"]


class NodeFile(BaseModel):
    """Model to store temporary files linked to specific nodes"""
    node = ForeignKey(Node, on_delete=CASCADE, related_name='files')
    key = CharField(max_length=255, help_text="Unique key for the file within the node")
    file = FileField(upload_to=node_file_upload_path)
    
    class Meta:
        unique_together = ['node', 'key']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.node} - {self.key}"
    
    def delete(self, *args, **kwargs):
        """Override delete to remove the actual file from filesystem"""
        if self.file:
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        super().delete(*args, **kwargs)


class ContainerStats(BaseModel):
    """Model to store container resource statistics during workflow execution"""
    workflow = ForeignKey(WorkFlow, on_delete=CASCADE, related_name='container_stats')
    
    # Resource metrics
    cpu_percent = FloatField(help_text="CPU usage percentage")
    memory_usage_mb = FloatField(help_text="Memory usage in MB")
    memory_percent = FloatField(help_text="Memory usage percentage")
    network_in_kb = FloatField(help_text="Network input in KB")
    network_out_kb = FloatField(help_text="Network output in KB")
    disk_read_mb = FloatField(help_text="Disk read in MB")
    disk_write_mb = FloatField(help_text="Disk write in MB")
    
    # Timestamp for the stat entry
    timestamp = DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            Index(fields=['workflow', 'timestamp']),
            Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.workflow.name} - {self.timestamp} - CPU: {self.cpu_percent}%"


class BrowserSession(BaseModel):
    """Model to represent browser automation sessions"""
    name = CharField(max_length=100)
    description = TextField(blank=True, null=True)
    browser_type = CharField(max_length=20, choices=[
        ('chromium', 'Chromium'),
        ('firefox', 'Firefox'),
        ('webkit', 'WebKit'),
    ], default='chromium')
    
    # Playwright configuration
    playwright_config = JSONField(default=dict, blank=True)
    
    # Session status
    status = CharField(max_length=20, choices=[
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('error', 'Error'),
    ], default='inactive')
    
    # Session metadata
    created_by = CharField(max_length=100, blank=True, null=True)
    tags = JSONField(default=list)
    
    def __str__(self):
        return f"{self.name}({self.id})"
    
    class Meta:
        ordering = ["-created_at"]


class DemoRequest(BaseModel):
    """Model to store demo booking requests from the landing page"""
    full_name = CharField(max_length=255)
    company_name = CharField(max_length=255)
    work_email = CharField(max_length=255)
    automation_needs = TextField()
    status = CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('contacted', 'Contacted'),
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], default='pending')
    notes = TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.full_name} - {self.company_name} ({self.status})"
    
    class Meta:
        ordering = ["-created_at"]

from django.contrib import admin
from .models import WorkFlow, Node, Connection, NodeFile, DemoRequest


@admin.register(WorkFlow)
class WorkFlowAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'description', 'task_id', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['name', 'description', 'task_id']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fields = ['id', 'name', 'description', 'task_id', 'created_at', 'updated_at']


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    list_display = ['id', 'workflow', 'node_type', 'x', 'y', 'created_at', 'updated_at']
    list_filter = ['workflow', 'node_type', 'created_at', 'updated_at']
    search_fields = ['workflow__name', 'node_type']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fields = ['id', 'workflow', 'node_type', 'x', 'y', 'form_values', 'config', 'created_at', 'updated_at']
    raw_id_fields = ['workflow']


@admin.register(Connection)
class ConnectionAdmin(admin.ModelAdmin):
    list_display = ['id', 'workflow', 'source_node', 'target_node', 'created_at', 'updated_at']
    list_filter = ['workflow', 'created_at', 'updated_at']
    search_fields = ['workflow__name', 'source_node__node_type', 'target_node__node_type']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fields = ['id', 'workflow', 'source_node', 'target_node', 'created_at', 'updated_at']
    raw_id_fields = ['workflow', 'source_node', 'target_node']


@admin.register(NodeFile)
class NodeFileAdmin(admin.ModelAdmin):
    list_display = ['id', 'node', 'key', 'created_at', 'updated_at']
    list_filter = ['node__workflow', 'node__node_type', 'created_at', 'updated_at']
    search_fields = ['node__workflow__name', 'node__node_type', 'key']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fields = ['id', 'node', 'key', 'file', 'created_at', 'updated_at']
    raw_id_fields = ['node']


@admin.register(DemoRequest)
class DemoRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'full_name', 'company_name', 'work_email', 'status', 'created_at']
    list_filter = ['status', 'created_at', 'updated_at']
    search_fields = ['full_name', 'company_name', 'work_email', 'automation_needs']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fields = ['id', 'full_name', 'company_name', 'work_email', 'automation_needs', 'status', 'notes', 'created_at', 'updated_at']
    ordering = ['-created_at']

from django.contrib import admin
from .models import WorkFlow, NodeType, Node, Connection


@admin.register(WorkFlow)
class WorkFlowAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'description', 'task_id', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['name', 'description', 'task_id']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fields = ['id', 'name', 'description', 'task_id', 'created_at', 'updated_at']


@admin.register(NodeType)
class NodeTypeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'description']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    list_display = ['id', 'workflow', 'node_type', 'position_x', 'position_y', 'created_at', 'updated_at']
    list_filter = ['workflow', 'node_type', 'created_at', 'updated_at']
    search_fields = ['workflow__name', 'node_type__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fields = ['id', 'workflow', 'node_type', 'position_x', 'position_y', 'data', 'created_at', 'updated_at']
    raw_id_fields = ['workflow', 'node_type']


@admin.register(Connection)
class ConnectionAdmin(admin.ModelAdmin):
    list_display = ['id', 'workflow', 'source_node', 'target_node', 'created_at', 'updated_at']
    list_filter = ['workflow', 'created_at', 'updated_at']
    search_fields = ['workflow__name', 'source_node__node_type__name', 'target_node__node_type__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fields = ['id', 'workflow', 'source_node', 'target_node', 'created_at', 'updated_at']
    raw_id_fields = ['workflow', 'source_node', 'target_node']
from django.contrib import admin
from .models import WorkFlow, Node, Connection, NodeFile, StandaloneNode, NodeGroup


@admin.register(WorkFlow)
class WorkFlowAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'description', 'task_id', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['name', 'description', 'task_id']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fields = ['id', 'name', 'description', 'task_id', 'created_at', 'updated_at']


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    list_display = ['id', 'workflow', 'node_type', 'position_x', 'position_y', 'created_at', 'updated_at']
    list_filter = ['workflow', 'node_type', 'created_at', 'updated_at']
    search_fields = ['workflow__name', 'node_type__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fields = ['id', 'workflow', 'node_type', 'position_x', 'position_y', 'data', 'form_values', 'created_at', 'updated_at']
    raw_id_fields = ['workflow', 'node_type']


@admin.register(Connection)
class ConnectionAdmin(admin.ModelAdmin):
    list_display = ['id', 'workflow', 'source_node', 'target_node', 'created_at', 'updated_at']
    list_filter = ['workflow', 'created_at', 'updated_at']
    search_fields = ['workflow__name', 'source_node__node_type__name', 'target_node__node_type__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fields = ['id', 'workflow', 'source_node', 'target_node', 'created_at', 'updated_at']
    raw_id_fields = ['workflow', 'source_node', 'target_node']


@admin.register(NodeGroup)
class NodeGroupAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'description', 'is_active', 'created_at', 'updated_at']
    list_filter = ['is_active', 'created_at', 'updated_at']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fields = ['id', 'name', 'description', 'icon', 'is_active', 'created_at', 'updated_at']


@admin.register(StandaloneNode)
class StandaloneNodeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'type', 'node_group', 'version', 'is_active', 'created_by', 'created_at', 'updated_at']
    list_filter = ['type', 'node_group', 'is_active', 'created_at', 'updated_at']
    search_fields = ['name', 'description', 'created_by']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fields = ['id', 'name', 'type', 'node_group', 'description', 'version', 'is_active', 'created_by', 'form_configuration', 'tags', 'logo', 'created_at', 'updated_at']
    raw_id_fields = ['node_group']


@admin.register(NodeFile)
class NodeFileAdmin(admin.ModelAdmin):
    list_display = ['id', 'node', 'key', 'created_at', 'updated_at']
    list_filter = ['node__workflow', 'node__node_type', 'created_at', 'updated_at']
    search_fields = ['node__workflow__name', 'node__node_type__name', 'key']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fields = ['id', 'node', 'key', 'file', 'created_at', 'updated_at']
    raw_id_fields = ['node']
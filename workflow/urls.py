from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter
from workflow.Views import ConnectionViewSet, NodeViewSet, WorkFlowViewSet, NodeFileViewSet, StandaloneNodeViewSet, NodeGroupViewSet
from workflow.Views.CeleryTaskView import CeleryTaskStatusView

router = DefaultRouter()
router.register("workflow", WorkFlowViewSet, basename="workflow")
router.register("node-groups", NodeGroupViewSet, basename="node-groups")
router.register("nodes", StandaloneNodeViewSet, basename="standalone-nodes")

workflow_router = NestedDefaultRouter(router, "workflow", lookup='workflow')
workflow_router.register("nodes", NodeViewSet, basename='workflow-nodes')
workflow_router.register("connections", ConnectionViewSet, basename='workflow-connections')

# Nested router for node files
node_router = NestedDefaultRouter(workflow_router, "nodes", lookup='node')
node_router.register("files", NodeFileViewSet, basename='node-files')

urlpatterns = [
    # Celery task status endpoint
    path('celery/task/<str:task_id>/status/', CeleryTaskStatusView.as_view(), name='celery-task-status'),
] + router.urls + workflow_router.urls + node_router.urls
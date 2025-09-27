from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter
from workflow.Views import ConnectionViewSet, NodeTypeViewSet, NodeViewSet, WorkFlowViewSet, NodeFileViewSet

router = DefaultRouter()
router.register("workflow", WorkFlowViewSet, basename="workflow")
router.register("node-types", NodeTypeViewSet, basename="node-type")

workflow_router = NestedDefaultRouter(router, "workflow", lookup='workflow')
workflow_router.register("nodes", NodeViewSet, basename='workflow-nodes')
workflow_router.register("connections", ConnectionViewSet, basename='workflow-connections')

# Nested router for node files
node_router = NestedDefaultRouter(workflow_router, "nodes", lookup='node')
node_router.register("files", NodeFileViewSet, basename='node-files')

urlpatterns = router.urls + workflow_router.urls + node_router.urls
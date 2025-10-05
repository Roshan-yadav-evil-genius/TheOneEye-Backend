from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Count, Q
from workflow.models import NodeGroup
from workflow.Serializers import NodeGroupSerializer, NodeGroupCreateSerializer, NodeGroupUpdateSerializer


class NodeGroupViewSet(ModelViewSet):
    serializer_class = NodeGroupSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        queryset = NodeGroup.objects.all()
        
        # Apply filters
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
            
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
            
        return queryset

    def get_serializer_class(self):
        if self.action == 'create':
            return NodeGroupCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return NodeGroupUpdateSerializer
        return NodeGroupSerializer

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get node group statistics"""
        queryset = self.get_queryset()
        
        stats = {
            'total_groups': queryset.count(),
            'active_groups': queryset.filter(is_active=True).count(),
            'inactive_groups': queryset.filter(is_active=False).count(),
            'groups_with_nodes': queryset.filter(nodes__isnull=False).distinct().count(),
            'groups_without_nodes': queryset.filter(nodes__isnull=True).count(),
        }
        
        return Response(stats)

    @action(detail=True, methods=['get'])
    def nodes(self, request, pk=None):
        """Get all nodes in this group"""
        node_group = self.get_object()
        nodes = node_group.nodes.all()
        
        # Apply additional filters if needed
        node_type = request.query_params.get('type')
        if node_type:
            nodes = nodes.filter(type=node_type)
            
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            nodes = nodes.filter(is_active=is_active.lower() == 'true')
        
        from workflow.Serializers import StandaloneNodeSerializer
        serializer = StandaloneNodeSerializer(nodes, many=True)
        return Response(serializer.data)

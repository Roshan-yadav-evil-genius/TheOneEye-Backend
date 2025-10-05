from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from workflow.models import StandaloneNode
from workflow.Serializers import StandaloneNodeSerializer, StandaloneNodeCreateSerializer, StandaloneNodeUpdateSerializer


class StandaloneNodeViewSet(ModelViewSet):
    serializer_class = StandaloneNodeSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        queryset = StandaloneNode.objects.all()
        
        # Apply filters
        node_type = self.request.query_params.get('type')
        if node_type:
            queryset = queryset.filter(type=node_type)
            
        node_group = self.request.query_params.get('node_group')
        if node_group:
            queryset = queryset.filter(node_group=node_group)
            
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
            
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(tags__icontains=search)
            )
            
        tags = self.request.query_params.getlist('tags')
        if tags:
            queryset = queryset.filter(tags__overlap=tags)
            
        return queryset

    def get_serializer_class(self):
        if self.action == 'create':
            return StandaloneNodeCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return StandaloneNodeUpdateSerializer
        return StandaloneNodeSerializer

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get node statistics"""
        queryset = self.get_queryset()
        
        stats = {
            'total_nodes': queryset.count(),
            'active_nodes': queryset.filter(is_active=True).count(),
            'inactive_nodes': queryset.filter(is_active=False).count(),
            'by_type': dict(queryset.values('type').annotate(count=Count('id')).values_list('type', 'count')),
            'by_node_group': dict(queryset.values('node_group__name').annotate(count=Count('id')).values_list('node_group__name', 'count')),
            'recent_created': queryset.filter(created_at__gte=timezone.now() - timedelta(days=7)).count()
        }
        
        return Response(stats)

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Create multiple nodes at once"""
        serializer = StandaloneNodeCreateSerializer(data=request.data, many=True)
        if serializer.is_valid():
            nodes = serializer.save()
            return Response(
                StandaloneNodeSerializer(nodes, many=True).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

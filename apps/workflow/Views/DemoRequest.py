from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from apps.workflow.models import DemoRequest
from apps.workflow.Serializers.DemoRequest import DemoRequestSerializer, DemoRequestCreateSerializer

class DemoRequestViewSet(ModelViewSet):
    queryset = DemoRequest.objects.all()
    serializer_class = DemoRequestSerializer
    
    def get_permissions(self):
        """
        Allow public access for creating demo requests (landing page),
        but require authentication for other operations.
        """
        if self.action == 'create':
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return DemoRequestCreateSerializer
        return DemoRequestSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            demo_request = serializer.save()
            response_serializer = DemoRequestSerializer(demo_request)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        """Update the status of a demo request"""
        demo_request = self.get_object()
        new_status = request.data.get('status')
        
        if new_status not in dict(DemoRequest._meta.get_field('status').choices):
            return Response(
                {'error': 'Invalid status'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        demo_request.status = new_status
        demo_request.notes = request.data.get('notes', demo_request.notes)
        demo_request.save()
        
        serializer = self.get_serializer(demo_request)
        return Response(serializer.data)

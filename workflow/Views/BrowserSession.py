from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework import status
from workflow.models import BrowserSession
from workflow.Serializers.BrowserSession import (
    BrowserSessionSerializer, 
    BrowserSessionCreateSerializer, 
    BrowserSessionUpdateSerializer
)
from rest_framework.decorators import action

class BrowserSessionViewSet(ModelViewSet):
    queryset = BrowserSession.objects.all()
    serializer_class = BrowserSessionSerializer
    
    def get_serializer_class(self):
        if self.action == 'create':
            return BrowserSessionCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return BrowserSessionUpdateSerializer
        return BrowserSessionSerializer
    
    @action(detail=True, methods=['post'])
    def launch_browser(self, request, pk=None):
        """Dummy launch browser action - just returns success message"""
        session = self.get_object()
        
        return Response({
            'message': f'Browser session "{session.name}" launched successfully (dummy)',
            'session_id': str(session.id),
            'browser_type': session.browser_type,
            'playwright_config': session.playwright_config
        })



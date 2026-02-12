from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.conf import settings
import os
import shutil
import structlog

logger = structlog.get_logger(__name__)
from apps.browsersession.models import BrowserSession, DomainThrottleRule
from apps.browsersession.serializers import (
    BrowserSessionSerializer,
    BrowserSessionCreateSerializer,
    BrowserSessionUpdateSerializer,
    DomainThrottleRuleSerializer,
    DomainThrottleRuleCreateSerializer,
)
from rest_framework.decorators import action


class BrowserSessionChoicesView(APIView):
    """Standalone view for session choices - no authentication required."""
    authentication_classes = []
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Return session choices for dropdown/select fields in forms."""
        sessions = BrowserSession.objects.all().values('id', 'name')
        choices = [{'id': str(s['id']), 'name': s['name']} for s in sessions]
        return Response(choices)

class BrowserSessionViewSet(ModelViewSet):
    queryset = BrowserSession.objects.all()
    serializer_class = BrowserSessionSerializer
    
    def get_serializer_class(self):
        if self.action == 'create':
            return BrowserSessionCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return BrowserSessionUpdateSerializer
        return BrowserSessionSerializer
    
    def create(self, request, *args, **kwargs):
        """Override create to create session directory after session creation"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        
        # Get the created session instance ID
        session_id = instance.id
        if session_id:
            # Create session directory: data/Browser/{session_id}
            sessions_dir = settings.BASE_DIR / 'data' / 'Browser'
            session_dir = sessions_dir / str(session_id)
            
            # Create directories if they don't exist
            try:
                os.makedirs(str(session_dir), exist_ok=True)
            except Exception as e:
                # Log error but don't fail the request
                logger.error("Error creating session directory", session_id=session_id, error=str(e), exc_info=True)
        
        # Create response using the full serializer (which includes id)
        headers = self.get_success_headers(serializer.data)
        response_serializer = BrowserSessionSerializer(instance)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def destroy(self, request, *args, **kwargs):
        """Override destroy to delete session directory before session deletion"""
        instance = self.get_object()
        session_id = instance.id
        
        # Delete session directory if it exists
        if session_id:
            sessions_dir = settings.BASE_DIR / 'data' / 'Browser'
            session_dir = sessions_dir / str(session_id)
            
            try:
                if os.path.exists(str(session_dir)):
                    shutil.rmtree(str(session_dir))
            except Exception as e:
                # Log error but don't fail the request
                logger.error("Error deleting session directory", session_id=session_id, error=str(e), exc_info=True)
        
        # Delete the session instance
        return super().destroy(request, *args, **kwargs)
    
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
    
    @action(detail=False, methods=['get'], authentication_classes=[], permission_classes=[AllowAny])
    def choices(self, request):
        """Return session choices for dropdown/select fields in forms."""
        sessions = BrowserSession.objects.all().values('id', 'name')
        choices = [{'id': str(s['id']), 'name': s['name']} for s in sessions]
        return Response(choices)
    
    @action(detail=True, methods=['get'], authentication_classes=[], permission_classes=[AllowAny])
    def config(self, request, pk=None):
        """
        Return session config for use by core BrowserManager.
        This endpoint is public to allow the core to fetch session config without auth.
        
        Returns:
            Session config with browser_type and playwright_config.
        """
        try:
            session = BrowserSession.objects.get(pk=pk)
            return Response({
                'id': str(session.id),
                'name': session.name,
                'browser_type': session.browser_type,
                'playwright_config': session.playwright_config,
                'status': session.status
            })
        except BrowserSession.DoesNotExist:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class DomainThrottleRuleViewSet(ModelViewSet):
    """CRUD for domain throttle rules scoped to a browser session (session_id in URL)."""
    serializer_class = DomainThrottleRuleSerializer

    def get_queryset(self):
        session_id = self.kwargs.get("session_id")
        if not session_id:
            return DomainThrottleRule.objects.none()
        return DomainThrottleRule.objects.filter(session_id=session_id)

    def get_serializer_class(self):
        if self.action == "create":
            return DomainThrottleRuleCreateSerializer
        return DomainThrottleRuleSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["session_id"] = self.kwargs.get("session_id")
        return context

    def perform_create(self, serializer):
        session_id = self.kwargs.get("session_id")
        session = BrowserSession.objects.get(id=session_id)
        serializer.save(session=session)

    def get_object(self):
        obj = super().get_object()
        session_id = self.kwargs.get("session_id")
        if str(obj.session_id) != str(session_id):
            from rest_framework.exceptions import NotFound
            raise NotFound()
        return obj
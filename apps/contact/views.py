from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import ContactSubmission
from .serializers import ContactSubmissionSerializer, ContactSubmissionCreateSerializer

class ContactSubmissionViewSet(viewsets.ModelViewSet):
    queryset = ContactSubmission.objects.all()
    serializer_class = ContactSubmissionSerializer
    permission_classes = [AllowAny]  # Allow unauthenticated access for public contact form

    def get_serializer_class(self):
        if self.action == 'create':
            return ContactSubmissionCreateSerializer
        return ContactSubmissionSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            contact_submission = serializer.save()
            return Response({
                'id': contact_submission.id,
                'message': 'Contact form submitted successfully',
                'status': 'success'
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def health(self, request):
        return Response({'status': 'ok', 'message': 'Contact service is running'})
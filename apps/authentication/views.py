from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .services import AuthenticationService
from .serializers import UserSerializer


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    Register a new user.
    View only handles HTTP request/response, delegates to service.
    """
    # TEMPORARILY DISABLED: New signups are currently disabled
    return Response(
        {'error': 'New user registration is temporarily disabled. Please contact support if you need access.'}, 
        status=status.HTTP_503_SERVICE_UNAVAILABLE
    )
    
    # When re-enabled, uncomment this:
    # response_data, status_code = AuthenticationService.register(request.data)
    # return Response(response_data, status=status_code)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    Login view that returns user data along with tokens.
    View only handles HTTP request/response, delegates to service.
    """
    username = request.data.get('username')
    password = request.data.get('password')
    
    response_data, status_code = AuthenticationService.login(username, password)
    return Response(response_data, status=status_code)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """
    Get current user data.
    View only handles HTTP request/response, delegates to service.
    """
    user_data = AuthenticationService.get_user_data(request.user)
    return Response(user_data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    Logout view that blacklists refresh token.
    View only handles HTTP request/response, delegates to service.
    """
    refresh_token = request.data.get("refresh")
    response_data, status_code = AuthenticationService.logout(refresh_token)
    return Response(response_data, status=status_code)
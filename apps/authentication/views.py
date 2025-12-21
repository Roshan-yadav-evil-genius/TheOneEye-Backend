from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .serializers import UserSerializer, RegisterSerializer

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    # TEMPORARILY DISABLED: New signups are currently disabled
    # TODO: Re-enable by removing this block when ready to accept new users
    return Response(
        {'error': 'New user registration is temporarily disabled. Please contact support if you need access.'}, 
        status=status.HTTP_503_SERVICE_UNAVAILABLE
    )
    
    # Original registration code (commented out for easy re-enabling)
    # serializer = RegisterSerializer(data=request.data)
    # if serializer.is_valid():
    #     user = serializer.save()
    #     refresh = RefreshToken.for_user(user)
    #     user_data = UserSerializer(user).data
    #     
    #     return Response({
    #         'user': user_data,
    #         'access': str(refresh.access_token),
    #         'refresh': str(refresh),
    #     }, status=status.HTTP_201_CREATED)
    # 
    # return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """Custom login view that returns user data along with tokens"""
    username = request.data.get('username')
    password = request.data.get('password')
    
    # TODO: Later we can support email login by uncommenting this:
    # email = request.data.get('email')
    # if email and not username:
    #     # Try to find user by email
    #     try:
    #         user_obj = User.objects.get(email=email)
    #         username = user_obj.username
    #     except User.DoesNotExist:
    #         pass
    
    if not username or not password:
        return Response(
            {'error': 'Username and password are required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Authenticate user
    user = authenticate(username=username, password=password)
    
    if user:
        refresh = RefreshToken.for_user(user)
        user_data = UserSerializer(user).data
        
        return Response({
            'user': user_data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })
    
    return Response(
        {'error': 'Invalid credentials'}, 
        status=status.HTTP_401_UNAUTHORIZED
    )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    try:
        refresh_token = request.data.get("refresh")
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)
    except Exception:
        return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)
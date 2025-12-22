"""
Authentication Service
Handles all authentication business logic, separated from views.
"""
from typing import Dict, Optional, Tuple
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from ..serializers import UserSerializer, RegisterSerializer


class AuthenticationService:
    """
    Service for handling authentication operations.
    Single responsibility: Authentication business logic.
    """
    
    @staticmethod
    def login(username: str, password: str) -> Tuple[Dict, int]:
        """
        Authenticate user and generate tokens.
        
        Args:
            username: Username for authentication
            password: Password for authentication
            
        Returns:
            Tuple of (response_data, status_code)
        """
        if not username or not password:
            return (
                {'error': 'Username and password are required'},
                status.HTTP_400_BAD_REQUEST
            )
        
        # Authenticate user
        user = authenticate(username=username, password=password)
        
        if not user:
            return (
                {'error': 'Invalid credentials'},
                status.HTTP_401_UNAUTHORIZED
            )
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        user_data = UserSerializer(user).data
        
        return (
            {
                'user': user_data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            },
            status.HTTP_200_OK
        )
    
    @staticmethod
    def register(user_data: Dict) -> Tuple[Dict, int]:
        """
        Register a new user.
        
        Args:
            user_data: Dictionary containing user registration data
            
        Returns:
            Tuple of (response_data, status_code)
        """
        serializer = RegisterSerializer(data=user_data)
        
        if not serializer.is_valid():
            return (
                serializer.errors,
                status.HTTP_400_BAD_REQUEST
            )
        
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        user_data_response = UserSerializer(user).data
        
        return (
            {
                'user': user_data_response,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            },
            status.HTTP_201_CREATED
        )
    
    @staticmethod
    def get_user_data(user: User) -> Dict:
        """
        Get serialized user data.
        
        Args:
            user: User instance
            
        Returns:
            Serialized user data
        """
        return UserSerializer(user).data
    
    @staticmethod
    def logout(refresh_token: Optional[str]) -> Tuple[Dict, int]:
        """
        Logout user by blacklisting refresh token.
        
        Args:
            refresh_token: Optional refresh token to blacklist
            
        Returns:
            Tuple of (response_data, status_code)
        """
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                # Token may already be blacklisted or invalid
                # Still return success to prevent information leakage
                pass
        
        return (
            {'message': 'Logout successful'},
            status.HTTP_200_OK
        )


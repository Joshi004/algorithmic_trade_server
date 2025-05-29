from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.conf import settings
from ..serializers.RegistrationSerializer import RegistrationSerializer
from ..serializers.LoginSerializer import LoginSerializer
# No longer needed as we use the header token validated by middleware
# from ..serializers.TokenRefreshSerializer import TokenRefreshSerializer
from ..utils.jwt_utils import generate_long_lived_token, generate_short_lived_token
import logging

# Get logger
logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = RegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response({
            "email": user.email,
            "public_id": user.public_id
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    logger.info("Login request received")
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        # Get user data from validated serializer
        user_data = {
            "public_id": str(serializer.validated_data["public_id"]),
            "email": serializer.validated_data["email"]
        }
        
        logger.info(f"Login successful for user: {user_data['email']}")
        
        # Generate both JWT tokens
        long_lived_token = generate_long_lived_token(user_data)
        short_lived_token = generate_short_lived_token(user_data)
        
        logger.info(f"Generated tokens - Long-lived: {long_lived_token[:20]}..., Short-lived: {short_lived_token[:20]}...")
        
        # Create response
        response = Response({
            "message": "Login successful",
            "user": {
                "email": user_data["email"],
                "public_id": user_data["public_id"]
            }
        }, status=status.HTTP_200_OK)
        
        # Set HTTP-only cookies for tokens
        # Long-lived token cookie (for refresh)
        response.set_cookie(
            'long_lived_token',
            long_lived_token,
            max_age=30 * 24 * 60 * 60,  # 30 days
            httponly=True,
            secure=getattr(settings, 'SECURE_COOKIES', False),  # Use HTTPS in production
            samesite='Lax',
            path='/'  # Ensure cookie is sent for all paths
        )
        
        # Short-lived token cookie (for API access) - Extended duration for better UX
        response.set_cookie(
            'short_lived_token',
            short_lived_token,
            max_age=2 * 60 * 60,  # 2 hours (was 15 minutes)
            httponly=True,
            secure=getattr(settings, 'SECURE_COOKIES', False),  # Use HTTPS in production
            samesite='Lax',
            path='/'  # Ensure cookie is sent for all paths
        )
        
        logger.info("Cookies set successfully")
        return response
    
    logger.warning(f"Login failed: {serializer.errors}")
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def refresh_token(request):
    """
    Endpoint to refresh a short-lived token using a valid long-lived token.
    If the long-lived token is invalid or expired, returns a 401 response
    that can trigger a redirect to the login page on the client.
    
    The token is validated by the middleware before this view is called.
    """
    logger.info("Token refresh request received")
    
    # The middleware has already validated the token and made user_data available
    if not hasattr(request, 'user_data'):
        logger.warning("No user_data found in refresh request")
        return Response({
            "error": "No valid token found",
            "redirect_to_login": True
        }, status=status.HTTP_401_UNAUTHORIZED)
        
    # Extract user data from the token (already validated by middleware)
    user_data = {
        "public_id": request.user_data["public_id"],
        "email": request.user_data["email"]
    }
    
    logger.info(f"Refreshing token for user: {user_data['email']}")
    
    # Generate new short-lived token
    short_lived_token = generate_short_lived_token(user_data)
    
    # Create response
    response = Response({
        "message": "Token refreshed successfully"
    }, status=status.HTTP_200_OK)
    
    # Update the short-lived token cookie
    response.set_cookie(
        'short_lived_token',
        short_lived_token,
        max_age=2 * 60 * 60,  # 2 hours (was 15 minutes)
        httponly=True,
        secure=getattr(settings, 'SECURE_COOKIES', False),  # Use HTTPS in production
        samesite='Lax',
        path='/'  # Ensure cookie is sent for all paths
    )
    
    logger.info("Token refreshed successfully")
    return response


@api_view(['POST'])
def logout(request):
    """
    Logout endpoint that clears authentication cookies
    """
    logger.info("Logout request received")
    
    response = Response({
        "message": "Logout successful"
    }, status=status.HTTP_200_OK)
    
    # Clear authentication cookies
    response.delete_cookie('long_lived_token')
    response.delete_cookie('short_lived_token')
    
    logger.info("Logout successful, cookies cleared")
    return response

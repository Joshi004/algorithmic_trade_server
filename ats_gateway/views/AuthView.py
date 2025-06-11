from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.conf import settings
from ..serializers.RegistrationSerializer import RegistrationSerializer
from ..serializers.LoginSerializer import LoginSerializer
# No longer needed as we use the header token validated by middleware
# from ..serializers.TokenRefreshSerializer import TokenRefreshSerializer
from ..utils.jwt_utils import generate_llt, generate_slt, SLT_EXPIRY_MINUTES
import logging
import datetime

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
            "first_name": user.first_name,
            "last_name": user.last_name
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
        
        # Log successful login without exposing email
        logger.info("User login successful")
        
        # Generate tokens
        llt = generate_llt(user_data)
        slt = generate_slt(user_data)
        
        # Log token generation without exposing token values
        logger.info("Authentication tokens generated successfully")
        
        # Calculate token expiry times for the frontend
        slt_expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=SLT_EXPIRY_MINUTES)
        slt_expires_in_seconds = SLT_EXPIRY_MINUTES * 60  # Convert minutes to seconds
        
        # Create response with expiry information
        response = Response({
            "message": "Login successful",
            "user": {
                "email": user_data["email"],
                "public_id": user_data["public_id"]
            },
            "token_info": {
                "slt_expires_in_seconds": slt_expires_in_seconds,
                "slt_expires_at": slt_expires_at.isoformat() + "Z"
            }
        }, status=status.HTTP_200_OK)
        
        # Set HTTP-only cookies for tokens
        # LLT cookie (for refresh)
        response.set_cookie(
            'llt',
            llt,
            max_age=30 * 24 * 60 * 60,  # 30 days
            httponly=True,
            secure=getattr(settings, 'SECURE_COOKIES', False),  # Use HTTPS in production
            samesite='Lax',
            path='/'  # Ensure cookie is sent for all paths
        )
        
        # SLT cookie (for API access)
        response.set_cookie(
            'slt',
            slt,
            max_age=slt_expires_in_seconds,  # Use the same expiry as the token
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
    Endpoint to refresh an SLT using a valid LLT.
    If the LLT is invalid or expired, returns a 401 response
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
    
    logger.info(f"Refreshing token for user ID: {user_data.get('user_id', 'unknown')}")
    
    # Generate new SLT
    slt = generate_slt(user_data)
    
    # Calculate token expiry times for the frontend
    slt_expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=SLT_EXPIRY_MINUTES)
    slt_expires_in_seconds = SLT_EXPIRY_MINUTES * 60  # Convert minutes to seconds
    
    # Create response with expiry information
    response = Response({
        "message": "Token refreshed successfully",
        "token_info": {
            "slt_expires_in_seconds": slt_expires_in_seconds,
            "slt_expires_at": slt_expires_at.isoformat() + "Z"
        }
    }, status=status.HTTP_200_OK)

    # Update the SLT cookie
    response.set_cookie(
        'slt',
        slt,
        max_age=slt_expires_in_seconds,  # Use the same expiry as the token
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
    response.delete_cookie('llt')
    response.delete_cookie('slt')
    
    logger.info("Logout successful, cookies cleared")
    return response

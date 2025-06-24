import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.conf import settings
from ..serializers.RegistrationSerializer import RegistrationSerializer
from ..serializers.LoginSerializer import LoginSerializer
from ..utils.jwt_utils import generate_llt, generate_slt, generate_websocket_token, SLT_EXPIRY_MINUTES, WEBSOCKET_TOKEN_EXPIRY_SECONDS
import datetime
from ats_base.logging_utils import create_service_logger, log_api_call
from ats_gateway.utils.logger import log




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
    log("Login request received", level="info")
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        # Get user data from validated serializer
        user_data = {
            "public_id": str(serializer.validated_data["public_id"]),
            "email": serializer.validated_data["email"],
            "first_name": serializer.validated_data["first_name"],
            "last_name": serializer.validated_data["last_name"]
        }
        
        log("User login successful", level="info")
        
        # Generate tokens
        llt = generate_llt(user_data)
        slt = generate_slt(user_data)
        
        log("Authentication tokens generated successfully", level="info")
        
        # Calculate token expiry times for the frontend
        slt_expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=SLT_EXPIRY_MINUTES)
        slt_expires_in_seconds = SLT_EXPIRY_MINUTES * 60  # Convert minutes to seconds
        
        # Create response with expiry information
        response = Response({
            "message": "Login successful",
            "user": {
                "email": user_data["email"],
                "first_name": user_data["first_name"],
                "last_name": user_data["last_name"]
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
        
        log("Cookies set successfully", level="info")
        return response
    
    log(f"Login failed: {serializer.errors}", level="warning")
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def refresh_token(request):
    """
    Endpoint to refresh an SLT using a valid LLT.
    If the LLT is invalid or expired, returns a 401 response
    that can trigger a redirect to the login page on the client.
    
    The token is validated by the middleware before this view is called.
    """
    log("Token refresh request received", level="info")
    
    # The middleware has already validated the token and made user_data available
    if not hasattr(request, 'user_data'):
        log("No user_data found in refresh request", level="warning")
        return Response({
            "error": "No valid token found",
            "redirect_to_login": True
        }, status=status.HTTP_401_UNAUTHORIZED)
        
    # Extract user data from the token (already validated by middleware)
    user_data = {
        "public_id": request.user_data["public_id"],
        "email": request.user_data["email"],
        "first_name": request.user_data.get("first_name"),
        "last_name": request.user_data.get("last_name")
    }
    
    log(f"Refreshing token for user ID: {user_data.get('user_id', 'unknown')}", level="info")
    
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
    
    log("Token refreshed successfully", level="info")
    return response


@api_view(['GET'])
def get_websocket_token(request):
    """
    WebSocket Token Endpoint with Enhanced Security (30-second expiration)
    
    This endpoint generates WebSocket-specific tokens with very short expiration times
    to minimize security risks from token exposure in browser network tabs.
    
    Security Features:
    - 30-second expiration (vs 15 minutes for regular SLT)
    - Special token type 'websocket' for identification
    - Scope limited to 'websocket_only' connections
    - Cannot be used for regular API calls
    
    The token is validated by the middleware before this view is called.
    """
    log("WebSocket token request received", level="info")
    
    # The middleware has already validated the token and made user_data available
    if not hasattr(request, 'user_data'):
        log("No user_data found in WebSocket token request", level="warning")
        return Response({
            "error": "No valid token found",
            "redirect_to_login": True
        }, status=status.HTTP_401_UNAUTHORIZED)
        
    # Extract user data from the token (already validated by middleware)
    user_data = {
        "public_id": request.user_data["public_id"],
        "email": request.user_data["email"],
        "first_name": request.user_data.get("first_name"),
        "last_name": request.user_data.get("last_name")
    }
    
    log("Generating WebSocket-specific token with 30-second expiration", level="info")
    
    # Generate a WebSocket-specific token with 30-second expiration
    websocket_token = generate_websocket_token(user_data)
    
    # Calculate token expiry times
    websocket_expires_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=WEBSOCKET_TOKEN_EXPIRY_SECONDS)
    
    # Return the WebSocket token in response body
    response = Response({
        "token": websocket_token,
        "token_info": {
            "expires_in_seconds": WEBSOCKET_TOKEN_EXPIRY_SECONDS,
            "expires_at": websocket_expires_at.isoformat() + "Z",
            "token_type": "websocket",
            "scope": "websocket_only"
        },
        "user": {
            "email": user_data["email"],
            "first_name": user_data.get("first_name"),
            "last_name": user_data.get("last_name")
        }
    }, status=status.HTTP_200_OK)
    
    log("WebSocket token provided successfully with 30-second expiration", level="info")
    return response


@api_view(['POST'])
@permission_classes([AllowAny])
def logout(request):
    """
    Logout endpoint that clears authentication cookies
    """
    log("Logout request received", level="info")
    
    response = Response({
        "message": "Logout successful"
    }, status=status.HTTP_200_OK)
    
    # Clear authentication cookies
    response.delete_cookie('llt')
    response.delete_cookie('slt')
    
    log("Logout successful, cookies cleared", level="info")
    return response

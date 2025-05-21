from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from ..serializers.RegistrationSerializer import RegistrationSerializer
from ..serializers.LoginSerializer import LoginSerializer
# No longer needed as we use the header token validated by middleware
# from ..serializers.TokenRefreshSerializer import TokenRefreshSerializer
from ..utils.jwt_utils import generate_long_lived_token, generate_short_lived_token


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
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        # Get user data from validated serializer
        user_data = {
            "public_id": str(serializer.validated_data["public_id"]),
            "email": serializer.validated_data["email"]
        }
        
        # Generate both JWT tokens
        long_lived_token = generate_long_lived_token(user_data)
        short_lived_token = generate_short_lived_token(user_data)
        
        # Return tokens to client
        return Response({
            "long_lived_token": long_lived_token,
            "short_lived_token": short_lived_token
        }, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def refresh_token(request):
    """
    Endpoint to refresh a short-lived token using a valid long-lived token.
    If the long-lived token is invalid or expired, returns a 401 response
    that can trigger a redirect to the login page on the client.
    
    Accepts GET requests with the long-lived token in the Authorization header.
    The token is validated by the middleware before this view is called.
    """
    # The middleware has already validated the token and made user_data available
    if not hasattr(request, 'user_data'):
        return Response({
            "error": "No valid token found in Authorization header",
            "redirect_to_login": True
        }, status=status.HTTP_401_UNAUTHORIZED)
        
    # Extract user data from the token (already validated by middleware)
    user_data = {
        "public_id": request.user_data["public_id"],
        "email": request.user_data["email"]
    }
    
    # Generate short-lived token
    short_lived_token = generate_short_lived_token(user_data)
    
    # Return the short-lived token to client
    return Response({
        "short_lived_token": short_lived_token
    }, status=status.HTTP_200_OK)

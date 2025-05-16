from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from ..serializers.RegistrationSerializer import RegistrationSerializer
from ..serializers.LoginSerializer import LoginSerializer
from ..utils.jwt_utils import generate_token


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
        
        # Generate JWT token
        token = generate_token(user_data)
        
        # Return token to client
        return Response({
            "token": token
        }, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
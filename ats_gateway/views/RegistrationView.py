from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from ..serializers.RegistrationSerializer import RegistrationSerializer


class RegistrationView(CreateAPIView):
    """
    API view for user registration.
    """
    serializer_class = RegistrationSerializer
    permission_classes = [AllowAny] 
from rest_framework import serializers
from django.core.exceptions import ValidationError
from ..models.User import User
from ..models.UserManager import validate_password


class RegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    """
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    public_id = serializers.UUIDField(read_only=True)
    
    class Meta:
        model = User
        fields = ['email', 'password', 'public_id']
    
    def validate_password(self, value):
        """
        Validate the password against the security requirements.
        """
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(str(e))
        return value
    
    def create(self, validated_data):
        """
        Create and return a new user using the validated data.
        """
        return User.objects.create_user(**validated_data) 
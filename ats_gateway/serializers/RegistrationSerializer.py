from rest_framework import serializers
from django.core.exceptions import ValidationError
from ..models.User import User
from ..models.UserManager import validate_password


class RegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    """
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    first_name = serializers.CharField(max_length=150, required=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name']
    
    def validate_password(self, value):
        """
        Validate the password against the security requirements.
        """
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(str(e))
        return value
    
    def validate_first_name(self, value):
        """
        Validate first_name is not empty.
        """
        if not value or not value.strip():
            raise serializers.ValidationError("First name is required and cannot be empty.")
        return value.strip()
    
    def validate_last_name(self, value):
        """
        Clean last_name by stripping whitespace.
        """
        if value:
            return value.strip()
        return value
    
    def create(self, validated_data):
        """
        Create and return a new user using the validated data.
        """
        return User.objects.create_user(**validated_data) 
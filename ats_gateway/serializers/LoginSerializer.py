from rest_framework import serializers
from django.contrib.auth import authenticate
from ..models.User import User
from django.core.exceptions import ObjectDoesNotExist
import bcrypt
import uuid


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    public_id = serializers.UUIDField(read_only=True)
    ssid = serializers.UUIDField(read_only=True)

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")

        try:
            user = User.objects.get(email=email)
        except ObjectDoesNotExist:
            raise serializers.ValidationError("Invalid email or password")

        if not user.is_active:
            raise serializers.ValidationError("Invalid email or password")

        # Validate password using bcrypt
        if not bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            raise serializers.ValidationError("Invalid email or password")

        # If valid, generate ssid (a new UUID in this example)
        data["public_id"] = user.public_id
        data["email"] = user.email
        # data["ssid"] = uuid.uuid4()  # You can replace this with session token logic if needed

        return data
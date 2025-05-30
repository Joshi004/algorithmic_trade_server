from ..utils.jwt_utils import decode_llt
from rest_framework import serializers
import uuid


class TokenRefreshSerializer(serializers.Serializer):
    """
    Serializer for refreshing short-lived tokens using a valid long-lived token.
    """
    long_lived_token = serializers.CharField(write_only=True)
    public_id = serializers.UUIDField(read_only=True)
    email = serializers.EmailField(read_only=True)

    def validate(self, data):
        """
        Validate the long-lived token and extract user data.
        """
        long_lived_token = data.get("long_lived_token")
        
        # Decode the long-lived token
        payload = decode_llt(long_lived_token)
        
        if not payload:
            raise serializers.ValidationError("Invalid or expired long-lived token")

        # Extract user data from the token
        data["public_id"] = payload["public_id"]
        data["email"] = payload["email"]

        return data

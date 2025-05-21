from rest_framework import serializers
from ..utils.jwt_utils import decode_long_lived_token

class TokenRefreshSerializer(serializers.Serializer):
    """
    Serializer for refreshing short-lived tokens using a valid long-lived token.
    """
    long_lived_token = serializers.CharField(required=True)
    
    def validate(self, data):
        """
        Validate the long-lived token and extract user data.
        """
        long_lived_token = data.get("long_lived_token")
        
        # Decode and validate the long-lived token
        payload = decode_long_lived_token(long_lived_token)
        if not payload:
            raise serializers.ValidationError("Invalid or expired token")
        
        # Add the user data from the token to the validated data
        data["user_data"] = {
            "public_id": payload["public_id"],
            "email": payload["email"]
        }
        
        return data

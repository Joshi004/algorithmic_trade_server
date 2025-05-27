import logging
from django.db import transaction
from integration_service.models.UserBrokerCredential import UserBrokerCredential
from django.utils.crypto import get_random_string
import base64
import hashlib
from cryptography.fernet import Fernet
from integration_service.lib.common.env_utils import get_env_variable

class BrokerService:
    def __init__(self):
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)
    
    def _get_encryption_key(self):
        """
        Get the encryption key from environment variables
        NOTE: This method is kept for future use but is not currently used.
        """
        secret = get_env_variable('BROKER_ENCRYPTION_SECRET')
        if not secret:
            raise ValueError("BROKER_ENCRYPTION_SECRET environment variable is not set")
        
        # Generate a key from the environment variable
        key = hashlib.sha256(secret.encode()).digest()
        return base64.urlsafe_b64encode(key)
    
    def _encrypt_secret(self, api_secret):
        """
        Encrypt the API secret before storing in the database
        NOTE: This method is kept for future use but is not currently used.
        """
        try:
            # Get encryption key from environment
            key = self._get_encryption_key()
            f = Fernet(key)
            
            # Encrypt the API secret
            encrypted_secret = f.encrypt(api_secret.encode())
            return encrypted_secret.decode()
        except Exception as e:
            self.logger.error(f"Error encrypting API secret: {str(e)}")
            raise
    
    def _decrypt_secret(self, encrypted_secret):
        """
        Decrypt the API secret from the database
        NOTE: This method is kept for future use but is not currently used.
        """
        try:
            # Get encryption key from environment
            key = self._get_encryption_key()
            f = Fernet(key)
            
            # Decrypt the API secret
            decrypted_secret = f.decrypt(encrypted_secret.encode())
            return decrypted_secret.decode()
        except Exception as e:
            self.logger.error(f"Error decrypting API secret: {str(e)}")
            raise
    
    @transaction.atomic
    def register_broker(self, user_id, broker_name, api_key, api_secret):
        """
        Register a new broker for a user
        """
        try:
            # Store API secret as plain text (no encryption)
            # Note: Encryption will be reintroduced later
            
            # Create the broker credential
            credential = UserBrokerCredential.create_broker_credential(
                user_id=user_id,
                broker_name=broker_name,
                api_key=api_key,
                api_secret=api_secret  # Store as plain text
            )
            
            return {
                "status": "success",
                "data": {
                    "credential_id": credential.id,
                    "broker_name": credential.broker_name,
                    "is_default": credential.is_default,
                    "status": credential.status
                }
            }
        except Exception as e:
            self.logger.error(f"Error registering broker: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def set_default_broker(self, user_id, credential_id):
        """
        Set a broker as the default for a user
        """
        try:
            credential = UserBrokerCredential.set_as_default(credential_id, user_id)
            return {
                "status": "success",
                "data": {
                    "credential_id": credential.id,
                    "broker_name": credential.broker_name,
                    "is_default": credential.is_default
                }
            }
        except Exception as e:
            self.logger.error(f"Error setting default broker: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_user_brokers(self, user_id):
        """
        Get all brokers registered for a user
        """
        try:
            credentials = UserBrokerCredential.objects.filter(user_id=user_id)
            result = []
            for cred in credentials:
                result.append({
                    "credential_id": cred.id,
                    "broker_name": cred.broker_name,
                    "is_default": cred.is_default,
                    "status": cred.status,
                    "created_at": cred.created_at
                })
            
            return {
                "status": "success",
                "data": result,
                "meta": {
                    "count": len(result)
                }
            }
        except Exception as e:
            self.logger.error(f"Error getting user brokers: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            } 
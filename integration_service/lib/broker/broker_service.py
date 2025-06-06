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
        Get the encryption key from environment variables for broker API secrets.
        
        Environment Variable: BROKER_API_ENCRYPTION_SECRET
        This key is used to encrypt/decrypt sensitive broker API credentials.
        
        Returns:
            bytes: Fernet-compatible encryption key
            
        Raises:
            ValueError: If the environment variable is not set
        """
        secret = get_env_variable('BROKER_API_ENCRYPTION_SECRET')
        if not secret:
            raise ValueError(
                "BROKER_API_ENCRYPTION_SECRET environment variable is required for broker credential encryption."
            )
        
        # Generate a key from the environment variable
        key = hashlib.sha256(secret.encode()).digest()
        return base64.urlsafe_b64encode(key)
    
    def _encrypt_value(self, value):
        """
        Encrypt a value before storing in the database.
        
        Args:
            value (str): The value to encrypt
            
        Returns:
            str: Encrypted value as a string
        """
        if not value:
            return value
            
        key = self._get_encryption_key()
        f = Fernet(key)
        encrypted_value = f.encrypt(value.encode())
        return encrypted_value.decode()
    
    def _decrypt_value(self, encrypted_value):
        """
        Decrypt a value from the database.
        
        Args:
            encrypted_value (str): The encrypted value from database
            
        Returns:
            str: Decrypted value
        """
        if not encrypted_value:
            return encrypted_value
            
        key = self._get_encryption_key()
        f = Fernet(key)
        decrypted_value = f.decrypt(encrypted_value.encode())
        return decrypted_value.decode()


    @transaction.atomic
    def register_broker(self, user_id, broker_name, api_key, api_secret):
        """
        Register a new broker for a user.
        
        All sensitive fields (api_key, api_secret) are encrypted before storage.
        
        Args:
            user_id: User's unique identifier
            broker_name: Name of the broker (zerodha)
            api_key: Broker API key (will be encrypted)
            api_secret: Broker API secret (will be encrypted)
            
        Returns:
            dict: Success/error response with credential details
        """
        try:
            # Encrypt sensitive fields
            encrypted_api_key = self._encrypt_value(api_key)
            encrypted_api_secret = self._encrypt_value(api_secret)
            
            # Create the broker credential with encrypted values
            credential = UserBrokerCredential.create_broker_credential(
                user_id=user_id,
                broker_name=broker_name,
                api_key=encrypted_api_key,
                api_secret=encrypted_api_secret
            )
            
            self.logger.info(f"Broker credential stored with encrypted API key and secret")
            
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
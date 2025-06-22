import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from django.db import transaction
from integration_service.models.UserBrokerCredential import UserBrokerCredential
from django.utils.crypto import get_random_string
import base64
import hashlib
from cryptography.fernet import Fernet
from integration_service.lib.common.env_utils import get_env_variable
from integration_service.lib.utils.logger import log



class BrokerService:
    def __init__(self):
        pass
    
    def _get_encryption_key(self):
        # Get encryption secret from environment and convert to Fernet-compatible key
        secret = get_env_variable('BROKER_API_ENCRYPTION_SECRET')
        if not secret:
            raise ValueError(
                "BROKER_API_ENCRYPTION_SECRET environment variable is required for broker credential encryption."
            )
        
        # Generate 32-byte key from secret and encode for Fernet
        key = hashlib.sha256(secret.encode()).digest()
        return base64.urlsafe_b64encode(key)
    
    def _encrypt_value(self, value):
        # Encrypt string value for secure database storage
        if not value:
            return value
            
        key = self._get_encryption_key()
        f = Fernet(key)
        # Convert string to bytes, encrypt, then back to string for database
        encrypted_value = f.encrypt(value.encode())
        return encrypted_value.decode()
    
    def _decrypt_value(self, encrypted_value):
        # Decrypt stored value back to original string
        if not encrypted_value:
            return encrypted_value
            
        key = self._get_encryption_key()
        f = Fernet(key)
        # Convert string to bytes, decrypt, then back to string
        decrypted_value = f.decrypt(encrypted_value.encode())
        return decrypted_value.decode()

    @transaction.atomic
    def register_broker(self, user_id, broker_name, api_key, api_secret):
        # Register new broker with encrypted credentials
        try:
            # Encrypt sensitive fields before storing
            encrypted_api_key = self._encrypt_value(api_key)
            encrypted_api_secret = self._encrypt_value(api_secret)
            
            # Create credential record with encrypted values
            credential = UserBrokerCredential.create_broker_credential(
                user_id=user_id,
                broker_name=broker_name,
                api_key=encrypted_api_key,
                api_secret=encrypted_api_secret
            )
            
            log(f"Broker credential stored with encrypted API key and secret", level="info")
            
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
            log(f"Error registering broker: {str(e)}", level="error")
            return {
                "status": "error",
                "error": str(e)
            }

    def set_default_broker(self, user_id, credential_id):
        # Set specific broker as default for user
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
            log(f"Error setting default broker: {str(e)}", level="error")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_user_brokers(self, user_id):
        # Get all registered brokers for user
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
            log(f"Error getting user brokers: {str(e)}", level="error")
            return {
                "status": "error",
                "error": str(e)
            } 
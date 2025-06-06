import logging
from kiteconnect import KiteConnect
import requests
from django.db import transaction
from integration_service.models.UserBrokerCredential import UserBrokerCredential
from integration_service.lib.broker.broker_service import BrokerService

class KiteUser:
    def __init__(self, user_id=None):
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)
        self.user_id = user_id
        self.api_key = None
        self.api_secret = None
        self.access_token = None
        self.credential = None
        self.broker_service = BrokerService()
        self._load_credentials()
    
    def _load_credentials(self):
        """Load Kite credentials from database for the user"""
        if not self.user_id:
            return
        
        try:
            # Get the default credential for Zerodha (Kite)
            self.credential = UserBrokerCredential.get_default_credential(
                user_id=self.user_id, 
                broker_name="zerodha"
            )
            
            if self.credential:
                self.logger.info(f"Found credential {self.credential.id} for user {self.user_id}")
                self.logger.info(f"Encrypted API key length: {len(self.credential.api_key) if self.credential.api_key else 'None'}")
                
                # Decrypt credentials for use
                self.api_key = self.broker_service._decrypt_value(self.credential.api_key)
                self.api_secret = self.broker_service._decrypt_value(self.credential.api_secret)
                
                self.logger.info(f"Decrypted API key: '{self.api_key}' (length: {len(self.api_key) if self.api_key else 'None'})")
                self.logger.info(f"API key starts with: '{self.api_key[:10] if self.api_key and len(self.api_key) >= 10 else self.api_key}'...")
                
                if self.credential.access_token:
                    self.access_token = self.broker_service._decrypt_value(self.credential.access_token)
            else:
                self.logger.warning(f"No default credential found for user {self.user_id}")
                
        except Exception as e:
            self.logger.error(f"Error loading credentials: {str(e)}")
            self.logger.error(f"Credential details: {self.credential.id if self.credential else 'None'}")
            raise
            
    def _save_access_token(self, user_data):
        """
        Save access token and session data to the database and update status to active.
        
        Since we successfully exchanged tokens with Zerodha, the credentials are validated.
        
        Args:
            user_data: Complete response from Zerodha's generate_session() call
        """
        if not self.user_id or not self.credential:
            return
        
        try:
            # Encrypt and save tokens
            encrypted_access_token = self.broker_service._encrypt_value(user_data["access_token"])
            encrypted_public_token = self.broker_service._encrypt_value(user_data.get("public_token", ""))
            encrypted_refresh_token = self.broker_service._encrypt_value(user_data.get("refresh_token", ""))
            
            # Update all token fields
            self.credential.access_token = encrypted_access_token
            self.credential.public_token = encrypted_public_token  
            self.credential.refresh_token = encrypted_refresh_token
            self.credential.kite_user_id = user_data.get("user_id")  # Save Kite user ID (not encrypted)
            
            # If this is the first successful token exchange, mark as active
            if self.credential.status == 'pending_verification':
                self.credential.status = 'active'
                self.credential.validation_error = None
                # Use login_time from Zerodha as last_refreshed_at
                self.credential.last_refreshed_at = user_data.get("login_time")
                self.logger.info(f"Credential {self.credential.id} validated and activated through successful token exchange")
            
            self.credential.save()
            self.access_token = user_data["access_token"]  # Keep decrypted for current session
            
        except Exception as e:
            self.logger.error(f"Error saving access token and session data: {str(e)}")
            # Mark as pending_verification if save fails
            if self.credential.status == 'pending_verification':
                self.credential.status = 'pending_verification'
                self.credential.validation_error = f"Failed to save session data: {str(e)}"
                self.credential.save()
    
    def get_instance(self):
        kite_obj = KiteConnect(api_key=self.api_key)
        if self.access_token:
            kite_obj.set_access_token(self.access_token)
        return kite_obj

    @transaction.atomic
    def set_session(self, request_token):   
        try:
            kite = KiteConnect(api_key=self.api_key)
            user_data = kite.generate_session(request_token, api_secret=self.api_secret)
            self.logger.info(f"User data post set session from Kite: {user_data}")
            
            # Validate that we received the required access_token
            if not user_data or "access_token" not in user_data:
                error_msg = "Failed to get access token from Kite session"
                self.logger.error(error_msg)
                # Update credential status to reflect the failure
                if self.credential:
                    self.credential.status = 'pending_verification'
                    self.credential.validation_error = error_msg
                    self.credential.save()
                raise ValueError(error_msg)
            
            # Validate other required fields
            required_fields = ["user_id", "email", "user_name"]
            missing_fields = [field for field in required_fields if field not in user_data]
            if missing_fields:
                error_msg = f"Missing required fields in session response: {missing_fields}"
                self.logger.error(error_msg)
                if self.credential:
                    self.credential.status = 'pending_verification'
                    self.credential.validation_error = error_msg
                    self.credential.save()
                raise ValueError(error_msg)
            
            kite.set_access_token(user_data["access_token"])
            
            # Save the access token to the database (also validates credentials)
            self._save_access_token(user_data)
            
            # Return public data with safe access
            public_data = {
                "avatar_url": user_data.get("avatar_url", ""),
                "email": user_data.get("email", ""),
                "exchanges": user_data.get("exchanges", []),
                "login_time": user_data.get("login_time", ""),
                "order_types": user_data.get("order_types", []),
                "user_id": user_data.get("user_id", ""),
                "products": user_data.get("products", []),
                "user_name": user_data.get("user_name", ""),
                "user_shortname": user_data.get("user_shortname", ""),
                "user_type": user_data.get("user_type", ""),
            }
            return public_data
            
        except Exception as e:
            self.logger.error(f"Error setting session: {str(e)}")
            # Update credential status if available
            if self.credential:
                self.credential.status = 'pending_verification'
                self.credential.validation_error = f"Session setup failed: {str(e)}"
                self.credential.save()
            raise
    
    def get_login_url(self):
        self.logger.info(f"Generating login URL with API key: '{self.api_key}' (length: {len(self.api_key) if self.api_key else 'None'})")
        
        if not self.api_key:
            self.logger.error("No API key available for login URL generation")
            return {"error": "No API key available"}
            
        kite = KiteConnect(api_key=self.api_key)
        login_url = kite.login_url()
        
        self.logger.info(f"Generated login URL: {login_url}")
        
        result = {
            "login_url": login_url
        }
        return result
    
    def get_profile_info(self): 
        kite = KiteConnect(api_key=self.api_key)
        if self.access_token:
            kite.set_access_token(self.access_token)
            userDetails = kite.profile()
            return userDetails
        else:
            return {"error": "No access token available"} 
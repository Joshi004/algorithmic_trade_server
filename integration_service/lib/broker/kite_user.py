import logging
from kiteconnect import KiteConnect
import requests
from django.db import transaction
from integration_service.models.UserBrokerCredential import UserBrokerCredential

class KiteUser:
    def __init__(self, user_id=None):
        logging.basicConfig(level=logging.DEBUG)
        self.user_id = user_id
        self.api_key = None
        self.api_secret = None
        self.access_token = None
        self._load_credentials()
    
    def _load_credentials(self):
        """Load Kite credentials from database for the user"""
        if not self.user_id:
            return
        
        try:
            # Get the default credential for Zerodha (Kite)
            credential = UserBrokerCredential.get_default_credential(
                user_id=self.user_id, 
                broker_name="zerodha"
            )
            
            if credential:
                self.api_key = credential.api_key
                self.api_secret = credential.api_secret
                self.access_token = credential.access_token
        except Exception as e:
            logging.error(f"Error loading credentials: {str(e)}")
            
    def _save_access_token(self, access_token):
        """Save access token to the database"""
        if not self.user_id:
            return
        
        try:
            # Get the default credential for Zerodha (Kite)
            credential = UserBrokerCredential.get_default_credential(
                user_id=self.user_id, 
                broker_name="zerodha"
            )
            
            if credential:
                credential.access_token = access_token
                credential.save()
                self.access_token = access_token
        except Exception as e:
            logging.error(f"Error saving access token: {str(e)}")
    
    def get_instance(self):
        kite_obj = KiteConnect(api_key=self.api_key)
        if self.access_token:
            kite_obj.set_access_token(self.access_token)
        return kite_obj

    @transaction.atomic
    def set_session(self, request_token):   
        kite = KiteConnect(api_key=self.api_key)
        user_data = kite.generate_session(request_token, api_secret=self.api_secret)
        kite.set_access_token(user_data["access_token"])
        
        # Save the access token to the database
        self._save_access_token(user_data["access_token"])
        
        # Return public data
        public_data = {
            "avatar_url": user_data["avatar_url"],
            "email": user_data["email"],
            "exchanges": user_data["exchanges"],
            "login_time": user_data["login_time"],
            "order_types": user_data["order_types"],
            "user_id": user_data["user_id"],
            "products": user_data["products"],
            "user_name": user_data["user_name"],
            "user_shortname": user_data["user_shortname"],
            "user_type": user_data["user_type"],
        }
        return public_data
    
    def get_login_url(self):
        kite = KiteConnect(api_key=self.api_key)
        login_url = kite.login_url()
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
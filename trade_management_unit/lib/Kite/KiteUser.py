import logging
from kiteconnect import KiteConnect
import requests
from trade_management_unit.models.UserConfiguration import UserConfiguration

class KiteUser:
    def __init__(self, user_id=1):  # Default user_id as 1 for backward compatibility
        self.user_id = user_id
        logging.basicConfig(level=logging.DEBUG)
        # Get credentials from database
        self.api_key = UserConfiguration.get_attribute(user_id, 'api_key')
        self.api_secret = UserConfiguration.get_attribute(user_id, 'api_secret')
        self.access_token = UserConfiguration.get_attribute(user_id, 'access_token')
        
        if not self.api_key or not self.api_secret:
            logging.error(f"API credentials not found for user_id {user_id}. Make sure they are set in the database.")
       
    def get_instance(self):
        if not self.api_key or not self.access_token:
            logging.error("Missing API credentials - cannot initialize Kite instance")
            return None
            
        kite_obj = KiteConnect(api_key=self.api_key)
        kite_obj.set_access_token(self.access_token)
        return kite_obj

    def set_session(self, request_token):   
        if not self.api_key or not self.api_secret:
            logging.error("Missing API credentials - cannot set session")
            return {"error": "API credentials not configured"}
            
        kite = KiteConnect(api_key=self.api_key)
        user_data = kite.generate_session(request_token, api_secret=self.api_secret)
        kite.set_access_token(user_data["access_token"])
        
        # Save access token to the database
        UserConfiguration.set_attribute(self.user_id, 'access_token', user_data["access_token"])
        self.access_token = user_data["access_token"]
       
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
        if not self.api_key:
            logging.error("Missing API key - cannot generate login URL")
            return {"error": "API key not configured"}
            
        kite = KiteConnect(api_key=self.api_key)
        login_url = kite.login_url()
        result = {
            "login_url": login_url
        }
        return result
    
    def get_profile_info(self): 
        if not self.api_key or not self.access_token:
            logging.error("Missing API credentials - cannot get profile info")
            return {"error": "API credentials not configured"}
            
        kite = KiteConnect(api_key=self.api_key)
        kite.set_access_token(self.access_token)
        userDetails = kite.profile()
        return userDetails


        
        


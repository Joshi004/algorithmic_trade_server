
import logging
from kiteconnect import KiteConnect
import requests
from trade_management_unit.lib.common.EnvFile import EnvFile

class KiteUser:
    def __init__(self):
        self.env = EnvFile('.env')
        logging.basicConfig(level=logging.DEBUG)
        self.api_key = self.env.read("api_key")
        self.api_secret = self.env.read("api_secret")
        self.access_token = self.env.read("access_token")
       
    
    def set_session(self,request_token):   
        print("Setting Session With Token : ",request_token)
        kite = KiteConnect(api_key=self.api_key)
        user_data = kite.generate_session(request_token, api_secret=self.api_secret)
        print("Git Access Token Successfully",user_data)
        kite.set_access_token(user_data["access_token"])
        self.env.write("access_token",user_data["access_token"])
        self.access_token = user_data["access_token"]
       
        public_data = {
            "avatar_url":user_data["avatar_url"],
            "email":user_data["email"],
            "exchanges":user_data["exchanges"],
            "login_time":user_data["login_time"],
            "order_types":user_data["order_types"],
            "user_id":user_data["user_id"],
            "products":user_data["products"],
            "user_name":user_data["user_name"],
            "user_shortname":user_data["user_shortname"],
            "user_type":user_data["user_type"],
        }
        return public_data
    
    def get_login_url(self):
        # print("In get login URL")
        kite = KiteConnect(api_key=self.api_key)
        login_url = kite.login_url()
        result = {
            "login_url" : login_url
        }
        # print("returning",result)
        return result
    
    def get_profile_info(self): 
        kite = KiteConnect(api_key=self.api_key)
        kite.set_access_token(self.access_token)
        userDetails = kite.profile()
        return userDetails


        
        


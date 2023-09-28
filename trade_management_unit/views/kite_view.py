from django.shortcuts import HttpResponse, render, redirect
from django.http import JsonResponse
import json
from django.core import serializers
from trade_management_unit.lib.Kite.KiteUser import KiteUser
from django.core import serializers


def set_session(request,*args,**kwvrgs):
    # This entire thing should be in Seperate App
    body  =  request.body.decode("utf-8")
    json_data = json.loads(body)  # Parse the JSON data 
    token = json_data["request_token"] #USE JWT to send token here
    kite_user = KiteUser()
    response = kite_user.set_session(token)
    return JsonResponse(response, status=200, content_type='application/json')

def get_login_url(request,*args,**kwvrgs):
    query_paramas  =  request.GET
    kite_user = KiteUser()
    response = kite_user.get_login_url()
    return JsonResponse(response, status=200, content_type='application/json')


def get_profile_info(request,*args,**kwvrgs):
    query_paramas  =  request.GET
    kite_user = KiteUser()
    response = kite_user.get_profile_info()
    return JsonResponse(response, status=200, content_type='application/json')

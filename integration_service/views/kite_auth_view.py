from django.shortcuts import HttpResponse, render, redirect
from django.http import JsonResponse
import json
from django.core import serializers
from integration_service.lib.broker.kite_user import KiteUser

def set_session(request, *args, **kwargs):
    """
    Set Kite session for a user using the request token
    """
    if request.method != 'POST':
        return JsonResponse({
            "status": "error",
            "error": "Method not allowed"
        }, status=405)
    
    try:
        # Get the request data
        body = request.body.decode("utf-8")
        json_data = json.loads(body)
        token = json_data.get("request_token")
        
        if not token:
            return JsonResponse({
                "status": "error",
                "error": "Request token is required"
            }, status=400)
        
        # Extract user_id from the request (assuming it's set by auth middleware)
        user_id = request.user_data.get('public_id') if hasattr(request, 'user_data') else json_data.get('user_id')
        
        if not user_id:
            return JsonResponse({
                "status": "error",
                "error": "User ID is required"
            }, status=400)
        
        kite_user = KiteUser(user_id)
        response = kite_user.set_session(token)
        return JsonResponse(response, status=200, content_type='application/json')
        
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "error": str(e)
        }, status=500)

def get_login_url(request, *args, **kwargs):
    """
    Get Kite login URL for a user
    """
    if request.method != 'GET':
        return JsonResponse({
            "status": "error",
            "error": "Method not allowed"
        }, status=405)
    
    try:
        # Extract user_id from the request (assuming it's set by auth middleware)
        user_id = request.user_data.get('public_id') if hasattr(request, 'user_data') else request.GET.get('user_id')
        
        if not user_id:
            return JsonResponse({
                "status": "error",
                "error": "User ID is required"
            }, status=400)
        
        kite_user = KiteUser(user_id)
        response = kite_user.get_login_url()
        return JsonResponse(response, status=200, content_type='application/json')
        
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "error": str(e)
        }, status=500)

def get_profile_info(request, *args, **kwargs):
    """
    Get Kite profile information for a user
    """
    if request.method != 'GET':
        return JsonResponse({
            "status": "error",
            "error": "Method not allowed"
        }, status=405)
    
    try:
        # Extract user_id from the request (assuming it's set by auth middleware)
        user_id = request.user_data.get('public_id') if hasattr(request, 'user_data') else request.GET.get('user_id')
        
        if not user_id:
            return JsonResponse({
                "status": "error",
                "error": "User ID is required"
            }, status=400)
        
        kite_user = KiteUser(user_id)
        response = kite_user.get_profile_info()
        return JsonResponse(response, status=200, content_type='application/json')
        
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "error": str(e)
        }, status=500) 
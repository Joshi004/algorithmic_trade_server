from django.shortcuts import HttpResponse, render, redirect
from django.http import JsonResponse
import json
from integration_service.lib.broker.kite_user import KiteUser
from integration_service.models.UserBrokerCredential import UserBrokerCredential

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
    Get Kite login URL for a user.
    Returns login URL for any default credentials - validation happens during actual API calls.
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
        
        # Check if user has broker credentials
        credential = UserBrokerCredential.get_default_credential(
            user_id=user_id
        )
        
        if not credential:
            # No broker credentials found, return response indicating this
            return JsonResponse({
                "status": "error",
                "error": "No broker credentials found",
                "error_code": "NO_BROKER_CREDENTIALS",
                "message": "Please register your broker credentials first",
                "redirect_to": "broker_registration"
            }, status=400)
        
        # Broker credentials exist, proceed with login URL generation
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
        
        # Check if the response contains an error
        if isinstance(response, dict) and "error" in response:
            # Return error response with appropriate status code
            return JsonResponse({
                "status": "error",
                "error": response["error"],
                "error_code": "KITE_NOT_CONNECTED",
                "message": "Please connect to Zerodha first",
                "action_required": "connect_to_zerodha"
            }, status=400)
        
        # Success case - return profile data
        return JsonResponse({
            "status": "success",
            "data": response
        }, status=200, content_type='application/json')
        
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "error": str(e)
        }, status=500) 
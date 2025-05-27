from django.http import JsonResponse
import json
from integration_service.lib.broker.broker_service import BrokerService

def register_broker(request, *args, **kwargs):
    """
    API endpoint to register a new broker for a user
    """
    if request.method != 'POST':
        return JsonResponse({
            "status": "error",
            "error": "Method not allowed"
        }, status=405)
    
    try:
        # Get the request data - handle both JSON and form data
        if request.content_type and 'application/json' in request.content_type:
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({
                    "status": "error",
                    "error": "Invalid JSON in request body"
                }, status=400)
        else:
            # Handle form data
            data = request.POST.dict()
            
        # Extract user_id from the request (assuming it's set by auth middleware)
        user_id = request.user_data.get('public_id') if hasattr(request, 'user_data') else data.get('user_id')
        
        if not user_id:
            return JsonResponse({
                "status": "error",
                "error": "User ID is required"
            }, status=400)
        
        # Validate required fields
        required_fields = ['broker_name', 'api_key', 'api_secret']
        for field in required_fields:
            if field not in data:
                return JsonResponse({
                    "status": "error",
                    "error": f"Missing required field: {field}"
                }, status=400)
        
        # Initialize the broker service
        broker_service = BrokerService()
        
        # Register the broker
        result = broker_service.register_broker(
            user_id=user_id,
            broker_name=data['broker_name'],
            api_key=data['api_key'],
            api_secret=data['api_secret']
        )
        
        if result['status'] == 'success':
            return JsonResponse(result, status=201)
        else:
            return JsonResponse(result, status=400)
    
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "error": str(e)
        }, status=500)

def get_user_brokers(request, *args, **kwargs):
    """
    API endpoint to get all brokers registered for a user
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
        
        # Initialize the broker service
        broker_service = BrokerService()
        
        # Get all brokers for the user
        result = broker_service.get_user_brokers(user_id)
        
        if result['status'] == 'success':
            return JsonResponse(result, status=200)
        else:
            return JsonResponse(result, status=400)
    
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "error": str(e)
        }, status=500)

def set_default_broker(request, *args, **kwargs):
    """
    API endpoint to set a broker as the default for a user
    """
    if request.method != 'POST':
        return JsonResponse({
            "status": "error",
            "error": "Method not allowed"
        }, status=405)
    
    try:
        # Get the request data - handle both JSON and form data
        if request.content_type and 'application/json' in request.content_type:
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({
                    "status": "error",
                    "error": "Invalid JSON in request body"
                }, status=400)
        else:
            # Handle form data
            data = request.POST.dict()
        
        # Extract user_id from the request (assuming it's set by auth middleware)
        user_id = request.user_data.get('public_id') if hasattr(request, 'user_data') else data.get('user_id')
        
        if not user_id:
            return JsonResponse({
                "status": "error",
                "error": "User ID is required"
            }, status=400)
        
        # Validate required fields
        if 'credential_id' not in data:
            return JsonResponse({
                "status": "error",
                "error": "Missing required field: credential_id"
            }, status=400)
        
        # Initialize the broker service
        broker_service = BrokerService()
        
        # Set the default broker
        result = broker_service.set_default_broker(user_id, data['credential_id'])
        
        if result['status'] == 'success':
            return JsonResponse(result, status=200)
        else:
            return JsonResponse(result, status=400)
    
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "error": str(e)
        }, status=500) 
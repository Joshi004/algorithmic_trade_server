import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from django.http import JsonResponse
from trade_management_unit.lib.TradeSession.TradeSession import TradeSession
from trade_management_unit.models.TradeSession import TradeSession as TradeSessionModel
from trade_management_unit.views.helpers.trade_session_helper import TradeSessionViewHelper
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from ats_base.logging_utils import create_service_logger
from trade_management_unit.lib.common.Utils.custome_logger import log

# Logger utility imported from trade_management_unit.lib.common.Utils.custome_logger


def initiate_trade_session(request, *args, **kwargs):
    """
    API endpoint to initiate a trade session.
    Thin view layer - delegates parameter validation to helper and business logic to library.
    """
    try:
        # Validate authentication
        user_id_str, auth_error = TradeSessionViewHelper.validate_authentication(request)
        if auth_error:
            return auth_error
        
        # Validate and extract parameters
        params, param_error = TradeSessionViewHelper.validate_and_extract_initiate_session_params(request)
        if param_error:
            return param_error
        
        # Delegate business logic to library
        result = TradeSession.initiate_trade_session(
            user_id_str=user_id_str,
            **params
        )
        
        return JsonResponse(result, status=200)
        
    except ValueError as e:
        return JsonResponse({
            'error': str(e),
            'message': 'Invalid input provided'
        }, status=400)
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'message': 'Failed to initiate trade session'
        }, status=500)


def get_new_session_param_options(request, *args, **kwargs):
    """
    API endpoint to get dynamic parameters for trade session initialization.
    Returns available algorithms and trading frequencies for the frontend form.
    """
    try:
        # Delegate to library method
        response_data = TradeSession.get_session_param_options()
        
        return JsonResponse(response_data, status=200)
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'message': 'Failed to fetch session parameter options'
        }, status=500)


@api_view(['GET'])
def get_active_trade_sessions(request):
    """
    Get active trade sessions with optional filtering by scanning algorithm and frequency.
    
    Query Parameters:
        scanning_algo_id (int, optional): Filter by scanning algorithm ID
        trading_frequency (str, optional): Filter by trading frequency
    
    Returns:
        JSON response with active trade sessions
    """
    try:
        # Extract and validate query parameters
        scanning_algo_id = request.GET.get('scanning_algo_id')
        trading_frequency = request.GET.get('trading_frequency')
        
        log("Validating and extracting parameters for active sessions query", level="debug")
        
        # Validate scanning_algo_id if provided
        if scanning_algo_id is not None:
            try:
                scanning_algo_id = int(scanning_algo_id)
            except (ValueError, TypeError):
                log("Parameter validation failed for active sessions query", level="warning")
                return JsonResponse({
                    'error': 'Invalid scanning_algo_id parameter',
                    'message': 'scanning_algo_id must be a valid integer'
                }, status=400)
        
        log("Querying active trade sessions", level="debug")
        
        # Use the model method to fetch active sessions
        active_sessions = TradeSession.get_active_sessions(
            scanning_algo_id=scanning_algo_id,
            trading_frequency=trading_frequency
        )
        
        log("Active trade sessions query completed", level="info")
        
        return JsonResponse({
            'status': 'success',
            'data': active_sessions,
            'meta': {
                'count': len(active_sessions),
                'filters': {
                    'scanning_algo_id': scanning_algo_id,
                    'trading_frequency': trading_frequency
                }
            }
        }, status=200)
        
    except Exception as e:
        log("Failed to fetch active trade sessions", level="error")
        return JsonResponse({
            'status': 'error',
            'error': 'Failed to fetch active trade sessions',
            'message': str(e)
        }, status=500)


def get_user_trade_sessions(request, *args, **kwargs):
    """
    API endpoint to get all trade sessions for a specific user with optional filtering.
    Thin view layer - delegates parameter validation to helper and business logic to library.
    """
    try:
        # Validate authentication
        user_id_str, auth_error = TradeSessionViewHelper.validate_authentication(request)
        if auth_error:
            return auth_error
        
        # Validate and extract parameters
        params, param_error = TradeSessionViewHelper.validate_and_extract_user_trade_sessions_params(request)
        if param_error:
            return param_error
        
        # Delegate business logic to library
        result = TradeSession.get_user_trade_sessions(
            user_id_str=user_id_str,
            **params
        )
        
        return JsonResponse(result, status=200)
        
    except ValueError as e:
        return JsonResponse({
            'error': str(e),
            'message': 'Invalid input provided'
        }, status=400)
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'message': 'Failed to fetch user trade sessions'
        }, status=500)


def get_trade_session_details(request, *args, **kwargs):
    """
    API endpoint to get comprehensive details of a specific trade session.
    Includes statistics like total trades, profit, success rate, etc.
    Thin view layer - delegates parameter validation to helper and business logic to library.
    """
    try:
        # Validate and extract parameters
        params, param_error = TradeSessionViewHelper.validate_and_extract_trade_session_details_params(request)
        if param_error:
            return param_error
        
        # Delegate business logic to library
        result = TradeSession.get_trade_session_details(
            trade_session_id=params['trade_session_id']
        )
        
        return JsonResponse(result, status=200)
        
    except ValueError as e:
        return JsonResponse({
            'error': str(e),
            'message': 'Invalid input provided'
        }, status=400)
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'message': 'Failed to fetch trade session details'
        }, status=500)


def pause_trade_session(request, *args, **kwargs):
    """
    API endpoint to pause a trade session.
    Thin view layer - delegates parameter validation to helper and business logic to library.
    """
    try:
        # Validate authentication
        user_id_str, auth_error = TradeSessionViewHelper.validate_authentication(request)
        if auth_error:
            return auth_error
        
        # Validate and extract parameters (including session ownership)
        params, param_error = TradeSessionViewHelper.validate_and_extract_pause_resume_params(request, user_id_str)
        if param_error:
            return param_error
        
        # Delegate business logic to library
        result = TradeSession.pause_trade_session(
            trade_session_id=params['trade_session_id'],
            user_id_str=user_id_str
        )
        
        return JsonResponse(result, status=200)
        
    except ValueError as e:
        return JsonResponse({
            'error': str(e),
            'message': 'Invalid input provided'
        }, status=400)
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'message': 'Failed to pause trade session'
        }, status=500)


def resume_trade_session(request, *args, **kwargs):
    """
    API endpoint to resume a trade session.
    Thin view layer - delegates parameter validation to helper and business logic to library.
    """
    try:
        # Validate authentication
        user_id_str, auth_error = TradeSessionViewHelper.validate_authentication(request)
        if auth_error:
            return auth_error
        
        # Validate and extract parameters (including session ownership)
        params, param_error = TradeSessionViewHelper.validate_and_extract_pause_resume_params(request, user_id_str)
        if param_error:
            return param_error
        
        # Delegate business logic to library
        result = TradeSession.resume_trade_session(
            trade_session_id=params['trade_session_id'],
            user_id_str=user_id_str
        )
        
        return JsonResponse(result, status=200)
        
    except ValueError as e:
        return JsonResponse({
            'error': str(e),
            'message': 'Invalid input provided'
        }, status=400)
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'message': 'Failed to resume trade session'
        }, status=500)

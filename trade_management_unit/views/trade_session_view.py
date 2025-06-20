import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from django.http import JsonResponse
from trade_management_unit.lib.TradeSession.TradeSession import TradeSession
from trade_management_unit.models.TradeSession import TradeSession as TradeSessionModel
from trade_management_unit.views.helpers.trade_session_helper import TradeSessionViewHelper
from ats_base.logging_utils import create_service_logger, log_api_call

# Create standardized logger for TMU views
logger = create_service_logger('trade_management_unit', 'views')


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


@log_api_call(logger, endpoint='get_active_trade_sessions', method='GET')
def get_active_trade_sessions(request, *args, **kwargs):
    """
    API endpoint to get active trade sessions with optional filtering.
    """
    try:
        logger.debug("Validating and extracting parameters for active sessions query")
        
        # Validate and extract parameters
        params, param_error = TradeSessionViewHelper.validate_and_extract_active_sessions_params(request)
        if param_error:
            logger.warning("Parameter validation failed for active sessions query")
            return param_error
        
        logger.debug("Querying active trade sessions", context={
            'scanning_algo_id': params['scanning_algo_id'],
            'trading_frequency': params['trading_frequency']
        })
        
        # Use the model method with optional parameters
        sessions = TradeSessionModel.fetch_active_trade_session(
            scanning_algo_id=params['scanning_algo_id'],
            trading_freq=params['trading_frequency']
        )
        
        logger.info("Active trade sessions query completed", context={
            'sessions_count': len(sessions)
        })
        
        # Format response data
        sessions_data = []
        for session in sessions:
            sessions_data.append({
                'id': session.id,
                'user_id': session.user_id.public_id,
                'trading_frequency': session.trading_frequency,
                'dummy': session.dummy,
                'status': session.status,
                'started_at': session.started_at.isoformat() if session.started_at else None,
                'closed_at': session.closed_at.isoformat() if session.closed_at else None,
                'scanning_algorithm_id': session.scanning_algorithm_id,
                'scanning_algorithm_name': session.scanning_algorithm.name,
                'initiation_algorithm_id': session.initiation_algorithm_id,
                'initiation_algorithm_name': session.initiation_algorithm.name,
                'termination_algorithm_id': session.termination_algorithm_id,
                'termination_algorithm_name': session.termination_algorithm.name
            })
        
        response_data = {
            'data': sessions_data,
            'meta': {'count': len(sessions_data)}
        }
        
        return JsonResponse(response_data, status=200)
        
    except Exception as e:
        logger.error("Failed to fetch active trade sessions", context={'error': str(e)})
        return JsonResponse({
            'error': str(e),
            'message': 'Failed to fetch active trade sessions'
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

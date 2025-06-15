from django.http import JsonResponse
from trade_management_unit.lib.TradeSession.TradeSession import TradeSession
from trade_management_unit.models.TradeSession import TradeSession as TradeSessionModel
from trade_management_unit.views.helpers.trade_session_helper import TradeSessionViewHelper
import logging


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


def get_active_trade_sessions(request, *args, **kwargs):
    """
    API endpoint to get active trade sessions with optional filtering.
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"[TMU] get_active_trade_sessions called with method: {request.method}")
        
        # Validate and extract parameters
        params, param_error = TradeSessionViewHelper.validate_and_extract_active_sessions_params(request)
        if param_error:
            return param_error
        
        logger.info(f"[TMU] Calling TradeSessionModel.fetch_active_trade_session with params")
        
        # Use the model method with optional parameters
        sessions = TradeSessionModel.fetch_active_trade_session(
            scanning_algo_id=params['scanning_algo_id'],
            trading_freq=params['trading_frequency']
        )
        
        logger.info(f"[TMU] Retrieved {len(sessions)} sessions from model")
        
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
                'initiation_algorithm_id': session.initiation_algorithm_id,
                'termination_algorithm_id': session.termination_algorithm_id
            })
        
        logger.info(f"[TMU] Formatted {len(sessions_data)} sessions data")
        
        response_data = {
            'data': sessions_data,
            'meta': {'count': len(sessions_data)}
        }
        
        logger.info(f"[TMU] Returning successful response with {len(sessions_data)} sessions")
        return JsonResponse(response_data, status=200)
        
    except Exception as e:
        logger.error(f"[TMU] Exception in get_active_trade_sessions: {str(e)}", exc_info=True)
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

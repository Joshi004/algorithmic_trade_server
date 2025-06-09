from django.http import JsonResponse
from trade_management_unit.lib.TradeSession.TradeSession import TradeSession
from trade_management_unit.models.TradeSession import TradeSession as TradeSessionModel
from ats_gateway.models.User import User
from trade_management_unit.Constants.TmuConstants import *
import logging


def initiate_trade_session(request, *args, **kwargs):
    """
    API endpoint to initiate a trade session.
    Thin view layer - delegates business logic to TradeSession library.
    """
    
    # Extract query parameters
    query_params = request.GET
    trading_frequency = query_params.get("trading_frequency")
    is_dummy = bool(query_params.get("dummy"))
    scanning_algorithm_id = query_params.get("scanning_algorithm_id")
    initiation_algorithm_id = query_params.get("initiation_algorithm_id")
    termination_algorithm_id = query_params.get("termination_algorithm_id")

    # Check authentication
    if not hasattr(request, 'user_data') or not request.user_data.get('public_id'):
        return JsonResponse({
            'error': 'Authentication required',
            'message': 'User must be authenticated to create a trade session'
        }, status=401)
    
    user_id_str = request.user_data.get('public_id')

    # Validate required parameters
    if not all([scanning_algorithm_id, initiation_algorithm_id, termination_algorithm_id, trading_frequency]):
        return JsonResponse({
            'error': 'Missing required parameters',
            'required_params': ['scanning_algorithm_id', 'initiation_algorithm_id', 'termination_algorithm_id', 'trading_frequency']
        }, status=400)

    try:
        # Delegate business logic to library
        result = TradeSession.initiate_trade_session(
            user_id_str=user_id_str,
            scanning_algorithm_id=scanning_algorithm_id,
            initiation_algorithm_id=initiation_algorithm_id,
            termination_algorithm_id=termination_algorithm_id,
            trading_frequency=trading_frequency,
            is_dummy=is_dummy
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
        
        query_params = request.GET
        scanning_algo_id = query_params.get("scanning_algo_id")
        trading_frequency = query_params.get("trading_frequency")
        
        logger.info(f"[TMU] Query params - scanning_algo_id: {scanning_algo_id}, trading_frequency: {trading_frequency}")
        
        # Convert to int if provided
        if scanning_algo_id:
            try:
                scanning_algo_id = int(scanning_algo_id)
                logger.info(f"[TMU] Converted scanning_algo_id to int: {scanning_algo_id}")
            except ValueError:
                logger.error(f"[TMU] Invalid scanning_algo_id conversion: {scanning_algo_id}")
                return JsonResponse({
                    'error': 'Invalid scanning_algo_id, must be an integer'
                }, status=400)
        
        logger.info(f"[TMU] Calling TradeSessionModel.fetch_active_trade_session with params")
        
        # Use the model method with optional parameters
        sessions = TradeSessionModel.fetch_active_trade_session(
            scanning_algo_id=scanning_algo_id,
            trading_freq=trading_frequency
        )
        
        logger.info(f"[TMU] Retrieved {len(sessions)} sessions from model")
        
        # Format response data
        sessions_data = []
        for session in sessions:
            sessions_data.append({
                'id': session.id,
                'user_id': session.user_id.public_id,
                'trading_frequency': session.trading_frequency,
                'is_dummy': session.dummy,
                'status': session.status,
                'started_at': session.started_at.isoformat() if session.started_at else None
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

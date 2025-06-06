from django.http import JsonResponse
from trade_management_unit.lib.TradeSession.TradeSession import TradeSession



from ats_gateway.models.User import User

from trade_management_unit.Constants.TmuConstants import *


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

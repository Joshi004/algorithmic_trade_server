from django.http import JsonResponse
from trade_management_unit.lib.Trade.trade import Trade
from trade_management_unit.lib.TradeSession.TradeSession import TradeSession
from trade_management_unit.lib.TradeSession.TradeSessionHelper import TradeSessionHelper
from channels.generic.websocket import AsyncWebsocketConsumer
from django.forms.models import model_to_dict
# from trade_management_unit.models.Algorithm import Algorithm
from trade_management_unit.lib.Kite.KiteTickhandler import KiteTickhandler
from trade_management_unit.models.ScanningAlgorithm import ScanningAlgorithm
from trade_management_unit.models.InitiationAlgorithm import InitiationAlgorithm
from trade_management_unit.models.TerminationAlgorithm import TerminationAlgorithm
from ats_gateway.models.User import User

from trade_management_unit.Constants.TmuConstants import *


def initiate_trade_session(request,*args,**kwvrgs):
        query_paramas  =  request.GET
        trading_frequency = query_paramas.get("trading_frequency")
        is_dummy = bool(query_paramas.get("dummy"))
        
        # Updated to use algorithm IDs instead of names
        scanning_algorithm_id = query_paramas.get("scanning_algorithm_id")
        initiation_algorithm_id = query_paramas.get("initiation_algorithm_id")
        termination_algorithm_id = query_paramas.get("termination_algorithm_id")

        # Get user_id from middleware (JWT authentication)
        if not hasattr(request, 'user_data') or not request.user_data.get('public_id'):
            error_response = {
                'error': 'Authentication required',
                'message': 'User must be authenticated to create a trade session'
            }
            return JsonResponse(error_response, status=401, content_type='application/json')
        
        user_id_str = request.user_data.get('public_id')

        # Validate required parameters
        if not all([scanning_algorithm_id, initiation_algorithm_id, termination_algorithm_id, trading_frequency]):
            error_response = {
                'error': 'Missing required parameters',
                'required_params': ['scanning_algorithm_id', 'initiation_algorithm_id', 'termination_algorithm_id', 'trading_frequency']
            }
            return JsonResponse(error_response, status=400, content_type='application/json')

        try:
            # Fetch the User instance from the authenticated user's UUID
            try:
                user = User.objects.get(public_id=user_id_str)
            except User.DoesNotExist:
                error_response = {
                    'error': f'Authenticated user does not exist in database',
                    'message': 'User account issue - please contact support'
                }
                return JsonResponse(error_response, status=400, content_type='application/json')
            
            trade_session = TradeSession(str(user.public_id), scanning_algorithm_id, initiation_algorithm_id, termination_algorithm_id, trading_frequency, is_dummy)
            response = {"trade_session_id": trade_session.trade_session_id}
            return JsonResponse(response, status=200, content_type='application/json')
        except ValueError as e:
            error_response = {
                'error': str(e),
                'message': 'Invalid algorithm ID provided'
            }
            return JsonResponse(error_response, status=400, content_type='application/json')
        except Exception as e:
            error_response = {
                'error': str(e),
                'message': 'Failed to initiate trade session'
            }
            return JsonResponse(error_response, status=500, content_type='application/json')


def get_new_session_param_options(request, *args, **kwargs):
    """
    API endpoint to get dynamic parameters for trade session initialization.
    Returns available algorithms and trading frequencies for the frontend form.
    """
    try:
        # Use the library method to get session parameters
        trade_session_helper = TradeSessionHelper()
        response_data = trade_session_helper.get_session_param_options()
        
        return JsonResponse(response_data, status=200, content_type='application/json')
        
    except Exception as e:
        error_response = {
            'error': str(e),
            'message': 'Failed to fetch session parameter options'
        }
        return JsonResponse(error_response, status=500, content_type='application/json')

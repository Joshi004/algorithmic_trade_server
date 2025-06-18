from django.http import JsonResponse
from django.utils.dateparse import parse_datetime
import logging
from trade_management_unit.models import ScanningAlgorithm, InitiationAlgorithm, TerminationAlgorithm


class TradeSessionViewHelper:
    """
    Helper class for trade session view parameter validations and utilities.
    """
    
    @staticmethod
    def validate_authentication(request):
        """
        Validate user authentication and extract user ID.
        
        Args:
            request: Django request object
            
        Returns:
            tuple: (user_id_str, error_response)
                   user_id_str is None if validation fails
                   error_response is None if validation succeeds
        """
        if not hasattr(request, 'user_data') or not request.user_data.get('public_id'):
            return None, JsonResponse({
                'error': 'Authentication required',
                'message': 'User must be authenticated to access trade sessions'
            }, status=401)
        
        return request.user_data.get('public_id'), None
    
    @staticmethod
    def validate_and_extract_user_trade_sessions_params(request):
        """
        Validate and extract parameters for get_user_trade_sessions endpoint.
        
        Args:
            request: Django request object
            
        Returns:
            tuple: (params_dict, error_response)
                   params_dict is None if validation fails
                   error_response is None if validation succeeds
        """
        query_params = request.GET
        
        # Extract all parameters
        scanning_algorithm_id = query_params.get("scanning_algorithm_id")
        initiation_algorithm_id = query_params.get("initiation_algorithm_id")
        termination_algorithm_id = query_params.get("termination_algorithm_id")
        dummy = query_params.get("dummy")
        trading_frequency = query_params.get("trading_frequency")
        status = query_params.get("status")
        started_at = query_params.get("started_at")
        closed_at = query_params.get("closed_at")
        
        # Validate algorithm IDs (convert to integers)
        if scanning_algorithm_id:
            try:
                scanning_algorithm_id = int(scanning_algorithm_id)
            except ValueError:
                return None, JsonResponse({
                    'error': 'Invalid scanning_algorithm_id, must be an integer'
                }, status=400)
        
        if initiation_algorithm_id:
            try:
                initiation_algorithm_id = int(initiation_algorithm_id)
            except ValueError:
                return None, JsonResponse({
                    'error': 'Invalid initiation_algorithm_id, must be an integer'
                }, status=400)
        
        if termination_algorithm_id:
            try:
                termination_algorithm_id = int(termination_algorithm_id)
            except ValueError:
                return None, JsonResponse({
                    'error': 'Invalid termination_algorithm_id, must be an integer'
                }, status=400)
        
        # Validate and convert dummy parameter
        is_dummy = None
        if dummy is not None:
            is_dummy = dummy.lower() in ('true', '1', 'yes')
        
        # Validate date parameters
        start_date = None
        end_date = None
        if started_at and closed_at:
            try:
                start_date = parse_datetime(started_at)
                end_date = parse_datetime(closed_at)
                
                if not start_date or not end_date:
                    return None, JsonResponse({
                        'error': 'Invalid date format. Use ISO format: YYYY-MM-DDTHH:MM:SS'
                    }, status=400)
                    
            except Exception as e:
                return None, JsonResponse({
                    'error': f'Error parsing dates: {str(e)}'
                }, status=400)
        
        # Return validated parameters
        params = {
            'scanning_algorithm_id': scanning_algorithm_id,
            'initiation_algorithm_id': initiation_algorithm_id,
            'termination_algorithm_id': termination_algorithm_id,
            'is_dummy': is_dummy,
            'trading_frequency': trading_frequency,
            'status': status,
            'start_date': start_date,
            'end_date': end_date
        }
        
        return params, None
    
    @staticmethod
    def validate_and_extract_initiate_session_params(request):
        """
        Validate and extract parameters for initiate_trade_session endpoint.
        
        Args:
            request: Django request object
            
        Returns:
            tuple: (params_dict, error_response)
                   params_dict is None if validation fails
                   error_response is None if validation succeeds
        """
        query_params = request.GET
        trading_frequency = query_params.get("trading_frequency")
        is_dummy = bool(query_params.get("dummy"))
        scanning_algorithm_name = query_params.get("scanning_algorithm_name")
        initiation_algorithm_name = query_params.get("initiation_algorithm_name")
        termination_algorithm_name = query_params.get("termination_algorithm_name")

        # Validate required parameters
        if not all([scanning_algorithm_name, initiation_algorithm_name, termination_algorithm_name, trading_frequency]):
            return None, JsonResponse({
                'error': 'Missing required parameters',
                'required_params': ['scanning_algorithm_name', 'initiation_algorithm_name', 'termination_algorithm_name', 'trading_frequency']
            }, status=400)

        # Convert algorithm names to IDs for database storage
        try:
            scanning_algorithm = ScanningAlgorithm.objects.get(name=scanning_algorithm_name)
            scanning_algorithm_id = scanning_algorithm.id
        except ScanningAlgorithm.DoesNotExist:
            return None, JsonResponse({
                'error': f'Invalid scanning algorithm name: {scanning_algorithm_name}'
            }, status=400)
            
        try:
            initiation_algorithm = InitiationAlgorithm.objects.get(name=initiation_algorithm_name)
            initiation_algorithm_id = initiation_algorithm.id
        except InitiationAlgorithm.DoesNotExist:
            return None, JsonResponse({
                'error': f'Invalid initiation algorithm name: {initiation_algorithm_name}'
            }, status=400)
            
        try:
            termination_algorithm = TerminationAlgorithm.objects.get(name=termination_algorithm_name)
            termination_algorithm_id = termination_algorithm.id
        except TerminationAlgorithm.DoesNotExist:
            return None, JsonResponse({
                'error': f'Invalid termination algorithm name: {termination_algorithm_name}'
            }, status=400)

        params = {
            'scanning_algorithm_id': scanning_algorithm_id,
            'initiation_algorithm_id': initiation_algorithm_id,
            'termination_algorithm_id': termination_algorithm_id,
            'trading_frequency': trading_frequency,
            'is_dummy': is_dummy
        }
        
        return params, None
    
    @staticmethod
    def validate_and_extract_active_sessions_params(request):
        """
        Validate and extract parameters for get_active_trade_sessions endpoint.
        
        Args:
            request: Django request object
            
        Returns:
            tuple: (params_dict, error_response)
                   params_dict is None if validation fails
                   error_response is None if validation succeeds
        """
        query_params = request.GET
        scanning_algo_id = query_params.get("scanning_algo_id")
        trading_frequency = query_params.get("trading_frequency")
        
        # Convert to int if provided
        if scanning_algo_id:
            try:
                scanning_algo_id = int(scanning_algo_id)
            except ValueError:
                return None, JsonResponse({
                    'error': 'Invalid scanning_algo_id, must be an integer'
                }, status=400)
        
        params = {
            'scanning_algo_id': scanning_algo_id,
            'trading_frequency': trading_frequency
        }
        
        return params, None
    
    @staticmethod
    def validate_and_extract_trade_session_details_params(request):
        """
        Validate and extract parameters for get_trade_session_details endpoint.
        
        Args:
            request: Django request object
            
        Returns:
            tuple: (params_dict, error_response)
                   params_dict is None if validation fails
                   error_response is None if validation succeeds
        """
        query_params = request.GET
        trade_session_id = query_params.get("trade_session_id")
        
        # Validate required parameter
        if not trade_session_id:
            return None, JsonResponse({
                'error': 'Missing required parameter: trade_session_id'
            }, status=400)
        
        # Convert to int and validate
        try:
            trade_session_id = int(trade_session_id)
        except ValueError:
            return None, JsonResponse({
                'error': 'Invalid trade_session_id, must be an integer'
            }, status=400)
        
        if trade_session_id <= 0:
            return None, JsonResponse({
                'error': 'trade_session_id must be a positive integer'
            }, status=400)
        
        params = {
            'trade_session_id': trade_session_id
        }
        
        return params, None 
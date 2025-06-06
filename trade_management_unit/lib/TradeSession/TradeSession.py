from  trade_management_unit.Constants.TmuConstants import *
from trade_management_unit.models.ScanningAlgorithm import ScanningAlgorithm
from trade_management_unit.models.InitiationAlgorithm import InitiationAlgorithm
from trade_management_unit.models.TerminationAlgorithm import TerminationAlgorithm
from trade_management_unit.lib.common.Utils.Utils import *
from trade_management_unit.models.TradeSession import TradeSession
from ats_gateway.models.User import User

class TradeSession():
   
    def __init__(self):
       pass
    
    
    def initiate_trade_session(self, user_id_str, scanning_algorithm_id, initiation_algorithm_id, termination_algorithm_id, trading_frequency, is_dummy):
        """
        Core business logic for trade session initiation.
        Handles both new session creation and existing session scenarios.
        
        Args:
            user_id_str (str): User's public ID from JWT authentication
            scanning_algorithm_id (str): Scanning algorithm ID from request
            initiation_algorithm_id (str): Initiation algorithm ID from request
            termination_algorithm_id (str): Termination algorithm ID from request
            trading_frequency (str): Trading frequency parameter
            is_dummy (bool): Whether this is a dummy/paper trading session
            
        Returns:
            dict: Response with success status, trade_session_id, message, and status
            
        Raises:
            ValueError: For validation errors
            Exception: For other errors
        """
        
        # Fetch the User instance from the authenticated user's UUID
        try:
            user = User.objects.get(public_id=user_id_str)
        except User.DoesNotExist:
            raise ValueError(f'Authenticated user does not exist in database')
        
        # Convert and validate algorithm IDs to integers
        try:
            scanning_algorithm_id = int(scanning_algorithm_id)
            initiation_algorithm_id = int(initiation_algorithm_id)
            termination_algorithm_id = int(termination_algorithm_id)
        except (ValueError, TypeError):
            raise ValueError('Algorithm IDs must be valid integers')
        
        # Use the model's fetch_or_create method which handles both new and existing sessions
        trade_session, message = TradeSession.fetch_or_create_trade_session(
            scanning_algorithm_id, 
            initiation_algorithm_id, 
            termination_algorithm_id, 
            trading_frequency, 
            is_dummy, 
            user
        )
        
        if trade_session is None:
            raise ValueError(message)  # This will contain the specific error message
        
        # Build success response - works for both new and existing sessions
        response = {
            "success": True,
            "trade_session_id": trade_session.id,
            "message": message,  # Either "New session created" or "Session already exists"
            "status": "new" if message == "New session created" else "existing"
        }
        
        return response

    def get_session_param_options(self):
        """
        Get all available parameters for creating a new trade session.
        Returns scanning algorithms, initiation algorithms, termination algorithms, 
        trading frequencies, and session types.
        """
        try:
            # Fetch all available scanning algorithms
            scanning_algorithms = ScanningAlgorithm.objects.all().values('id', 'name', 'display_name', 'description')
            scanning_algorithms_list = [
                {
                    'id': algo['id'],
                    'name': algo['name'],
                    'display_name': algo['display_name'] or algo['name'],
                    'description': algo['description'] or ''
                }
                for algo in scanning_algorithms
            ]
            
            # Fetch all available initiation algorithms
            initiation_algorithms = InitiationAlgorithm.objects.all().values('id', 'name', 'display_name', 'description')
            initiation_algorithms_list = [
                {
                    'id': algo['id'],
                    'name': algo['name'],
                    'display_name': algo['display_name'] or algo['name'],
                    'description': algo['description'] or ''
                }
                for algo in initiation_algorithms
            ]
            
            # Fetch all available termination algorithms
            termination_algorithms = TerminationAlgorithm.objects.all().values('id', 'name', 'display_name', 'description')
            termination_algorithms_list = [
                {
                    'id': algo['id'],
                    'name': algo['name'],
                    'display_name': algo['display_name'] or algo['name'],
                    'description': algo['description'] or ''
                }
                for algo in termination_algorithms
            ]
            
            # Get available trading frequencies from constants
            trading_frequencies = FREQUENCY
            
            # Define session types
            session_types = [
                {'id': 'dummy', 'name': 'Dummy', 'description': 'Paper trading mode for testing'},
                {'id': 'live', 'name': 'Live', 'description': 'Real trading mode'}
            ]
            
            # Build response structure
            response_data = {
                'data': {
                    'scanning_algorithms': scanning_algorithms_list,
                    'initiation_algorithms': initiation_algorithms_list,
                    'termination_algorithms': termination_algorithms_list,
                    'trading_frequencies': trading_frequencies,
                    'session_types': session_types
                },
                'meta': {
                    'scanning_algorithms_count': len(scanning_algorithms_list),
                    'initiation_algorithms_count': len(initiation_algorithms_list),
                    'termination_algorithms_count': len(termination_algorithms_list),
                    'trading_frequencies_count': len(trading_frequencies)
                }
            }
            
            return response_data
            
        except Exception as e:
            raise Exception(f"Failed to fetch session parameter options: {str(e)}")



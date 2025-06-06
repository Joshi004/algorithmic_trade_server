from trade_management_unit.Constants.TmuConstants import FREQUENCY
from trade_management_unit.models.ScanningAlgorithm import ScanningAlgorithm
from trade_management_unit.models.InitiationAlgorithm import InitiationAlgorithm
from trade_management_unit.models.TerminationAlgorithm import TerminationAlgorithm
from trade_management_unit.models.TradeSession import TradeSession as TradeSessionModel
from trade_management_unit.lib.common.event_publisher import get_trade_session_event_publisher
from ats_gateway.models.User import User


class TradeSession:
    
    @staticmethod
    def initiate_trade_session(user_id_str, scanning_algorithm_id, initiation_algorithm_id, termination_algorithm_id, trading_frequency, is_dummy):
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
            raise ValueError('Authenticated user does not exist in database')
        
        # Convert and validate algorithm IDs to integers
        try:
            scanning_algorithm_id = int(scanning_algorithm_id)
            initiation_algorithm_id = int(initiation_algorithm_id)
            termination_algorithm_id = int(termination_algorithm_id)
        except (ValueError, TypeError):
            raise ValueError('Algorithm IDs must be valid integers')
        
        # Use the model's fetch_or_create method which handles both new and existing sessions
        trade_session, message = TradeSessionModel.fetch_or_create_trade_session(
            scanning_algorithm_id, 
            initiation_algorithm_id, 
            termination_algorithm_id, 
            trading_frequency, 
            is_dummy, 
            user
        )
        
        if trade_session is None:
            raise ValueError(message)  # This will contain the specific error message
        
        # Publish event to Redis stream only for new session creation
        if message == "New session created":
            try:
                event_publisher = get_trade_session_event_publisher()
                event_publisher.publish_trade_session_initiated(trade_session, message)
            except Exception as e:
                # Log error but don't fail the session creation
                from trade_management_unit.lib.common.Utils.custome_logger import log
                log(f"Failed to publish trade session initiation event for session {trade_session.id}: {str(e)}", level="error")
        
        # Build success response - works for both new and existing sessions
        response = {
            "success": True,
            "trade_session_id": trade_session.id,
            "message": message,  # Either "New session created" or "Session already exists"
            "status": "new" if message == "New session created" else "existing"
        }
        
        return response

    @staticmethod
    def get_session_param_options():
        """
        Get all available parameters for creating a new trade session.
        Returns scanning algorithms, initiation algorithms, termination algorithms, 
        trading frequencies, and session types.
        """
        try:
            # Fetch all available algorithms - evaluate QuerySets once with list()
            scanning_algorithms = list(
                ScanningAlgorithm.objects.values('id', 'name', 'display_name', 'description')
            )
            
            initiation_algorithms = list(
                InitiationAlgorithm.objects.values('id', 'name', 'display_name', 'description')
            )
            
            termination_algorithms = list(
                TerminationAlgorithm.objects.values('id', 'name', 'display_name', 'description')
            )
            
            # Process algorithms to ensure display_name and description fallbacks
            for algo in scanning_algorithms:
                algo['display_name'] = algo['display_name'] or algo['name']
                algo['description'] = algo['description'] or ''
                
            for algo in initiation_algorithms:
                algo['display_name'] = algo['display_name'] or algo['name']
                algo['description'] = algo['description'] or ''
                
            for algo in termination_algorithms:
                algo['display_name'] = algo['display_name'] or algo['name']
                algo['description'] = algo['description'] or ''
            
            # Define session types
            session_types = [
                {'id': 'dummy', 'name': 'Dummy', 'description': 'Paper trading mode for testing'},
                {'id': 'live', 'name': 'Live', 'description': 'Real trading mode'}
            ]
            
            # Build response structure
            response_data = {
                'data': {
                    'scanning_algorithms': scanning_algorithms,
                    'initiation_algorithms': initiation_algorithms,
                    'termination_algorithms': termination_algorithms,
                    'trading_frequencies': FREQUENCY,
                    'session_types': session_types
                },
                'meta': {
                    'scanning_algorithms_count': len(scanning_algorithms),
                    'initiation_algorithms_count': len(initiation_algorithms),
                    'termination_algorithms_count': len(termination_algorithms),
                    'trading_frequencies_count': len(FREQUENCY)
                }
            }
            
            return response_data
            
        except Exception as e:
            raise Exception(f"Failed to fetch session parameter options: {str(e)}")



from trade_management_unit.Constants.TmuConstants import FREQUENCY
from trade_management_unit.models.ScanningAlgorithm import ScanningAlgorithm
from trade_management_unit.models.InitiationAlgorithm import InitiationAlgorithm
from trade_management_unit.models.TerminationAlgorithm import TerminationAlgorithm
from trade_management_unit.models.TradeSession import TradeSession as TradeSessionModel
from trade_management_unit.models.Trade import Trade
from trade_management_unit.models.ScannerEvent import ScannerEvent
from trade_management_unit.lib.common.event_publisher import get_trade_session_event_publisher
from ats_gateway.models.User import User
from django.db.models import Count, Sum, Max, Q
from decimal import Decimal
import logging


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

    @staticmethod
    def get_user_trade_sessions(user_id_str, scanning_algorithm_id=None, initiation_algorithm_id=None, 
                              termination_algorithm_id=None, is_dummy=None, trading_frequency=None, 
                              status=None, start_date=None, end_date=None):
        """
        Core business logic for fetching user trade sessions with optional filtering.
        
        Args:
            user_id_str (str): User's public ID from JWT authentication
            scanning_algorithm_id (int, optional): Filter by scanning algorithm ID
            initiation_algorithm_id (int, optional): Filter by initiation algorithm ID
            termination_algorithm_id (int, optional): Filter by termination algorithm ID
            is_dummy (bool, optional): Filter by dummy/live sessions
            trading_frequency (str, optional): Filter by trading frequency
            status (str, optional): Filter by session status
            start_date (datetime, optional): Start date for date range filtering
            end_date (datetime, optional): End date for date range filtering
            
        Returns:
            dict: Response with data array and metadata
            
        Raises:
            ValueError: For validation errors
            Exception: For other errors
        """
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"[TMU-Library] get_user_trade_sessions called for user: {user_id_str}")
            
            # Build query starting with user filter
            query = TradeSessionModel.objects.filter(user_id=user_id_str)
            logger.info(f"[TMU-Library] Base query: user_id={user_id_str}")
            
            # Apply optional filters
            if scanning_algorithm_id:
                query = query.filter(scanning_algorithm_id=scanning_algorithm_id)
                logger.info(f"[TMU-Library] Added filter: scanning_algorithm_id={scanning_algorithm_id}")
            
            if initiation_algorithm_id:
                query = query.filter(initiation_algorithm_id=initiation_algorithm_id)
                logger.info(f"[TMU-Library] Added filter: initiation_algorithm_id={initiation_algorithm_id}")
            
            if termination_algorithm_id:
                query = query.filter(termination_algorithm_id=termination_algorithm_id)
                logger.info(f"[TMU-Library] Added filter: termination_algorithm_id={termination_algorithm_id}")
            
            if is_dummy is not None:
                query = query.filter(dummy=is_dummy)
                logger.info(f"[TMU-Library] Added filter: dummy={is_dummy}")
            
            if trading_frequency:
                query = query.filter(trading_frequency=trading_frequency)
                logger.info(f"[TMU-Library] Added filter: trading_frequency={trading_frequency}")
            
            if status:
                query = query.filter(status=status)
                logger.info(f"[TMU-Library] Added filter: status={status}")
            
            # Handle date range filtering
            if start_date and end_date:
                query = query.filter(started_at__gte=start_date, started_at__lte=end_date)
                logger.info(f"[TMU-Library] Added date range filter: {start_date} to {end_date}")
            
            # Execute query and get results
            sessions = list(query.order_by('-started_at'))
            logger.info(f"[TMU-Library] Retrieved {len(sessions)} sessions from database")
            
            # Format response data with specified fields
            sessions_data = []
            for session in sessions:
                sessions_data.append({
                    'id': session.id,
                    'status': session.status,
                    'started_at': session.started_at.isoformat() if session.started_at else None,
                    'closed_at': session.closed_at.isoformat() if session.closed_at else None,
                    'dummy': session.dummy,
                    'is_active': session.is_active,
                    'initiation_algorithm_id': session.initiation_algorithm_id,
                    'termination_algorithm_id': session.termination_algorithm_id,
                    'scanning_algorithm_id': session.scanning_algorithm_id,
                    'trading_frequency': session.trading_frequency
                })
            
            response_data = {
                'data': sessions_data,
                'meta': {
                    'count': len(sessions_data),
                    'user_id': user_id_str
                }
            }
            
            logger.info(f"[TMU-Library] Returning successful response with {len(sessions_data)} sessions")
            return response_data
            
        except Exception as e:
            logger.error(f"[TMU-Library] Exception in get_user_trade_sessions: {str(e)}", exc_info=True)
            raise Exception(f"Failed to fetch user trade sessions: {str(e)}")

    @staticmethod
    def get_trade_session_details(trade_session_id):
        """
        Core business logic for fetching comprehensive trade session details.
        
        Args:
            trade_session_id (int): Trade session ID to get details for
            
        Returns:
            dict: Response with comprehensive trade session details
            
        Raises:
            ValueError: For validation errors
            Exception: For other errors
        """
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"[TMU-Library] get_trade_session_details called for session: {trade_session_id}")
            
            # Validate and fetch trade session
            try:
                trade_session = TradeSessionModel.objects.get(id=trade_session_id)
            except TradeSessionModel.DoesNotExist:
                raise ValueError(f"Trade session with ID {trade_session_id} does not exist")
            
            # 1. Get last activity from scanner_events table
            last_scanner_event = ScannerEvent.objects.filter(
                trade_session_id=str(trade_session_id)
            ).order_by('-timestamp').first()
            
            last_activity_at = None
            if last_scanner_event:
                last_activity_at = last_scanner_event.timestamp.isoformat()
            
            # 2. Get trade statistics from trades table
            trades_queryset = Trade.objects.filter(trade_session_id=trade_session_id)
            
            # Total trades executed
            total_trades = trades_queryset.count()
            
            # 3. Total number of long trades
            total_long_trades = trades_queryset.filter(view='long').count()
            
            # 4. Total number of short trades  
            total_short_trades = trades_queryset.filter(view='short').count()
            
            # 5. Total number of instruments scanned from scanner_events
            total_instruments_scanned = ScannerEvent.objects.filter(
                trade_session_id=str(trade_session_id)
            ).values('instrument_id').distinct().count()
            
            # 6. Active trades
            active_trades = trades_queryset.filter(is_active=True).count()
            
            # 7. Total profit - sum of net_profit for all trades
            total_profit_result = trades_queryset.aggregate(
                total_profit=Sum('net_profit')
            )
            total_profit = total_profit_result['total_profit'] or Decimal('0.00')
            
            # 8. Success percentage - trades with positive net_profit / total closed trades
            closed_trades = trades_queryset.filter(is_active=False)
            total_closed_trades = closed_trades.count()
            
            if total_closed_trades > 0:
                profitable_trades = closed_trades.filter(net_profit__gt=0).count()
                success_percentage = round((profitable_trades / total_closed_trades) * 100, 2)
            else:
                success_percentage = 0.0
            
            # Build comprehensive response
            response_data = {
                'data': {
                    # Basic session information (for refreshing accordion header)
                    'id': trade_session_id,
                    'user_id': trade_session.user_id.public_id,
                    'trading_frequency': trade_session.trading_frequency,
                    'dummy': trade_session.dummy,
                    'status': trade_session.status,
                    'started_at': trade_session.started_at.isoformat() if trade_session.started_at else None,
                    'closed_at': trade_session.closed_at.isoformat() if trade_session.closed_at else None,
                    'scanning_algorithm_id': trade_session.scanning_algorithm_id,
                    'initiation_algorithm_id': trade_session.initiation_algorithm_id,
                    'termination_algorithm_id': trade_session.termination_algorithm_id,
                    
                    # Detailed statistics for expanded view
                    'last_activity_at': last_activity_at,
                    'total_trades_executed': total_trades,
                    'total_long_trades': total_long_trades,
                    'total_short_trades': total_short_trades,
                    'total_instruments_scanned': total_instruments_scanned,
                    'active_trades': active_trades,
                    'total_profit': float(total_profit),
                    'success_percentage': success_percentage
                },
                'meta': {
                    'total_closed_trades': total_closed_trades,
                    'profitable_trades': closed_trades.filter(net_profit__gt=0).count() if total_closed_trades > 0 else 0,
                    'loss_making_trades': closed_trades.filter(net_profit__lt=0).count() if total_closed_trades > 0 else 0
                }
            }
            
            logger.info(f"[TMU-Library] Successfully compiled trade session details for session: {trade_session_id}")
            return response_data
            
        except ValueError as e:
            logger.error(f"[TMU-Library] Validation error in get_trade_session_details: {str(e)}")
            raise e
        except Exception as e:
            logger.error(f"[TMU-Library] Error in get_trade_session_details: {str(e)}", exc_info=True)
            raise Exception(f"Failed to fetch trade session details: {str(e)}")

    @staticmethod
    def pause_trade_session(trade_session_id: str, user_id_str: str) -> dict:
        """
        Core business logic for pausing a trade session.
        Performs direct database operations to update session status.
        
        Args:
            trade_session_id: Trade session ID to pause
            user_id_str: User's public ID from JWT authentication
            
        Returns:
            dict: Response with success status and updated session data
            
        Raises:
            ValueError: For validation errors
            Exception: For other errors
        """
        from trade_management_unit.lib.common.Utils.Utils import current_ist
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"[TMU-Library] pause_trade_session called for session: {trade_session_id}, user: {user_id_str}")
            
            # Get the trade session (validation already done in helper)
            trade_session = TradeSessionModel.objects.get(id=trade_session_id, user_id=user_id_str)
            
            # Validate current status allows pausing
            if trade_session.status != 'started':
                raise ValueError(f"Cannot pause session with status '{trade_session.status}'. Only 'started' sessions can be paused.")
            
            # Update session status and is_active
            trade_session.status = 'paused'
            trade_session.is_active = False
            trade_session.save()
            
            logger.info(f"[TMU-Library] Successfully paused trade session: {trade_session_id}")
            
            # Return success response
            response_data = {
                'success': True,
                'message': f'Trade session {trade_session_id} paused successfully',
                'data': {
                    'trade_session_id': str(trade_session.id),
                    'status': trade_session.status,
                    'is_active': trade_session.is_active,
                    'paused_at': current_ist().isoformat()
                }
            }
            
            return response_data
            
        except TradeSessionModel.DoesNotExist:
            raise ValueError(f"Trade session {trade_session_id} not found or does not belong to user")
        except Exception as e:
            logger.error(f"[TMU-Library] Error pausing trade session: {str(e)}", exc_info=True)
            raise Exception(f"Failed to pause trade session: {str(e)}")

    @staticmethod  
    def resume_trade_session(trade_session_id: str, user_id_str: str) -> dict:
        """
        Core business logic for resuming a trade session.
        Performs direct database operations to update session status.
        
        Args:
            trade_session_id: Trade session ID to resume
            user_id_str: User's public ID from JWT authentication
            
        Returns:
            dict: Response with success status and updated session data
            
        Raises:
            ValueError: For validation errors
            Exception: For other errors
        """
        from trade_management_unit.lib.common.Utils.Utils import current_ist
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"[TMU-Library] resume_trade_session called for session: {trade_session_id}, user: {user_id_str}")
            
            # Get the trade session (validation already done in helper)
            trade_session = TradeSessionModel.objects.get(id=trade_session_id, user_id=user_id_str)
            
            # Validate current status allows resuming
            if trade_session.status != 'paused':
                raise ValueError(f"Cannot resume session with status '{trade_session.status}'. Only 'paused' sessions can be resumed.")
            
            # Update session status and is_active
            trade_session.status = 'started'
            trade_session.is_active = True
            trade_session.save()
            
            logger.info(f"[TMU-Library] Successfully resumed trade session: {trade_session_id}")
            
            # Publish resume scanner event to ensure scanner is running
            try:
                event_publisher = get_trade_session_event_publisher()
                resume_event_success = event_publisher.publish_resume_scanner_event(trade_session)
                
                if resume_event_success:
                    logger.info(f"[TMU-Library] Successfully published resume scanner event for session: {trade_session_id}")
                else:
                    logger.warning(f"[TMU-Library] Failed to publish resume scanner event for session: {trade_session_id}")
                    
            except Exception as e:
                # Don't fail the resume operation if event publishing fails
                logger.error(f"[TMU-Library] Error publishing resume scanner event for session {trade_session_id}: {str(e)}")
            
            # Return success response
            response_data = {
                'success': True,
                'message': f'Trade session {trade_session_id} resumed successfully',
                'data': {
                    'trade_session_id': str(trade_session.id),
                    'status': trade_session.status,
                    'is_active': trade_session.is_active,
                    'resumed_at': current_ist().isoformat()
                }
            }
            
            return response_data
            
        except TradeSessionModel.DoesNotExist:
            raise ValueError(f"Trade session {trade_session_id} not found or does not belong to user")
        except Exception as e:
            logger.error(f"[TMU-Library] Error resuming trade session: {str(e)}", exc_info=True)
            raise Exception(f"Failed to resume trade session: {str(e)}")



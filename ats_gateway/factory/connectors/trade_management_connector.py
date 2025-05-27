import logging
from django.http import JsonResponse
from .base_connector import BaseServiceConnector
from trade_management_unit.views import (
    instrument_view, 
    trade_view, 
    kite_view, 
    scanner_algo_view, 
    portfolio_view,
    trade_session_view
)

logger = logging.getLogger(__name__)

class TradeManagementConnector(BaseServiceConnector):
    """Connector for the trade_management_unit service."""
    
    def __init__(self):
        """Initialize with the URL to view function mapping."""
        self.url_to_view_map = {
            "get_instruments": instrument_view.get_instruments,
            "update_instruments": instrument_view.update_instruments,
            "get_historical_data": instrument_view.get_historical_data,
            "get_quotes": trade_view.get_quotes,
            "get_all_trades_info": trade_view.get_all_trades_info,
            "set_session": kite_view.set_session,
            "get_login_url": kite_view.get_login_url,
            "get_profile_info": kite_view.get_profile_info,
            "get_eligible_instruments": scanner_algo_view.get_eligible_instruments,
            "get_udts_eligibility": scanner_algo_view.get_udts_eligibility,
            "get_udts_redcord": scanner_algo_view.get_udts_redcord,
            "get_holdings": portfolio_view.get_holdings,
            "get_positions": portfolio_view.get_positions,
            "get_orders": portfolio_view.get_orders,
            "get_orders_trades": portfolio_view.get_orders_trades,
            "get_order_history": portfolio_view.get_order_history,
            "place_order": portfolio_view.place_order,
            "initiate_trade_session": trade_session_view.initiate_trade_session,
            "get_new_session_param_options": trade_session_view.get_new_session_param_options,
            "get_trade_sessions": trade_session_view.get_trade_sessions,
            "resume_trade_session": trade_session_view.resume_trade_session,
            "session_active": trade_session_view.session_active,
            "terminate_trade_session": trade_session_view.terminate_trade_session,
        }
    
    def handle_request(self, request, path):
        """
        Handle requests for the trade management service.
        
        Args:
            request: The Django request object
            path: The path extracted from the URL
            
        Returns:
            HttpResponse: The response from the service
        """
        logger.info(f"TradeManagementConnector handling path: {path}")
        
        # Get the view function for this path
        view_func = self.url_to_view_map.get(path)
        
        if not view_func:
            logger.error(f"View function not found for path: {path}")
            return JsonResponse({
                "error": f"View not found for {path}"
            }, status=404)
            
        logger.info(f"Calling view function: {view_func.__name__}")
        
        try:
            # Call the view function directly
            response = view_func(request)
            logger.info(f"Response received from view")
            return response
            
        except Exception as e:
            logger.error(f"Error handling request: {str(e)}", exc_info=True)
            return JsonResponse({
                "error": str(e)
            }, status=500) 
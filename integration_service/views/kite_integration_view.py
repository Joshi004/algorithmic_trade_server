from django.http import JsonResponse
import json
import traceback
from integration_service.lib.broker.fetch_data import FetchData
from integration_service.lib.broker.portfolio import Portfolio
from integration_service.lib.broker.trade import Trade
from integration_service.lib.broker.instruments import InstrumentsProvider
from integration_service.lib.utils.logger import log

# Historical Data endpoints (from DataView)
def get_historical_data(request, *args, **kwargs):
    """
    API endpoint to get historical data for an instrument
    """
    if request.method != 'GET':
        return JsonResponse({
            "status": "error",
            "error": "Method not allowed"
        }, status=405)
    
    try:
        # Extract user_id from the request (assuming it's set by auth middleware)
        user_id = request.user_data.get('public_id') if hasattr(request, 'user_data') else request.GET.get('user_id')
        
        if not user_id:
            return JsonResponse({
                "status": "error",
                "error": "User ID is required"
            }, status=400)
        
        # Get query parameters
        symbol = request.GET.get('symbol')
        token = request.GET.get('token')
        interval = request.GET.get('interval')
        number_of_candles = request.GET.get('number_of_candles')
        trade_date = request.GET.get('trade_date')
        
        # Log the incoming request parameters
        log(f"[INTEGRATION_VIEW] Historical data request received: symbol={symbol}, token={token}, interval={interval}, candles={number_of_candles}, trade_date={trade_date}, user_id={user_id}")
        
        # Validate required parameters
        if not all([symbol, token, interval, number_of_candles]):
            missing_params = [param for param, value in [('symbol', symbol), ('token', token), ('interval', interval), ('number_of_candles', number_of_candles)] if not value]
            error_msg = f"Missing required parameters: {', '.join(missing_params)}"
            log(f"[INTEGRATION_VIEW] ❌ {error_msg}", level="error")
            return JsonResponse({
                "status": "error",
                "error": error_msg
            }, status=400)
        
        try:
            number_of_candles = int(number_of_candles)
        except ValueError:
            error_msg = "number_of_candles must be a valid integer"
            log(f"[INTEGRATION_VIEW] ❌ {error_msg}: received '{number_of_candles}'", level="error")
            return JsonResponse({
                "status": "error",
                "error": error_msg
            }, status=400)
        
        # Parse trade_date if provided
        parsed_trade_date = None
        if trade_date:
            try:
                from datetime import datetime
                parsed_trade_date = datetime.fromisoformat(trade_date)
                log(f"[INTEGRATION_VIEW] Trade date parsed: {parsed_trade_date}")
            except ValueError:
                error_msg = "trade_date must be in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
                log(f"[INTEGRATION_VIEW] ❌ {error_msg}: received '{trade_date}'", level="error")
                return JsonResponse({
                    "status": "error",
                    "error": error_msg
                }, status=400)
        
        # Initialize the fetch data service
        log(f"[INTEGRATION_VIEW] Initializing FetchData service for user {user_id}")
        fetch_data = FetchData(user_id)
        
        # Get historical data
        log(f"[INTEGRATION_VIEW] Calling fetch_historical_data_for_client for {symbol}")
        result = fetch_data.fetch_historical_data_for_client(
            symbol=symbol,
            token=token,
            interval=interval,
            number_of_candles=number_of_candles,
            trade_date=parsed_trade_date
        )
        
        # Log the result being returned
        data_size = len(result.get("data", []))
        log(f"[INTEGRATION_VIEW] Returning response for {symbol}: {data_size} candles")
        
        # Check if this is API success with zero data vs API failure
        api_success = result.get("meta", {}).get("api_success_status", True)
        
        if data_size == 0:
            if api_success:
                log(f"[INTEGRATION_VIEW] ⚠️ Returning ZERO data for {symbol} - API succeeded but no data available (likely expired instrument)", level="warning")
            else:
                log(f"[INTEGRATION_VIEW] ❌ Returning ZERO data for {symbol} - API failed: {result.get('meta', {}).get('api_error_message', 'Unknown error')}", level="error")
            log(f"[INTEGRATION_VIEW] Request details: token={token}, interval={interval}, candles={number_of_candles}", level="warning")
        else:
            # Log first and last candle for verification
            data = result.get("data", [])
            first_candle = data[0] if data else None
            last_candle = data[-1] if len(data) > 1 else data[0] if len(data) == 1 else None
            log(f"[INTEGRATION_VIEW] Sample candles for {symbol}: first={first_candle}, last={last_candle}")
        
        return JsonResponse({
            "status": "success",
            "data": result["data"],
            "meta": result["meta"]
        }, status=200)
        
    except Exception as e:
        error_msg = str(e)
        log(f"[INTEGRATION_VIEW] ❌ Exception in get_historical_data: {error_msg}", level="error")
        log(f"[INTEGRATION_VIEW] Request details: symbol={symbol if 'symbol' in locals() else 'N/A'}, token={token if 'token' in locals() else 'N/A'}", level="error")
        log(f"[INTEGRATION_VIEW] Full traceback: {traceback.format_exc()}", level="error")
        
        return JsonResponse({
            "status": "error",
            "error": error_msg
        }, status=500)

# Portfolio endpoints (from PortfolioView)
def get_holdings(request, *args, **kwargs):
    """
    API endpoint to get user holdings
    """
    if request.method != 'GET':
        return JsonResponse({
            "status": "error",
            "error": "Method not allowed"
        }, status=405)
    
    try:
        # Extract user_id from the request (assuming it's set by auth middleware)
        user_id = request.user_data.get('public_id') if hasattr(request, 'user_data') else request.GET.get('user_id')
        
        if not user_id:
            return JsonResponse({
                "status": "error",
                "error": "User ID is required"
            }, status=400)
        
        # Initialize the portfolio service
        portfolio = Portfolio(user_id)
        
        # Get holdings
        result = portfolio.get_holdings()
        
        return JsonResponse(result, status=200)
        
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "error": str(e)
        }, status=500)

def get_positions(request, *args, **kwargs):
    """
    API endpoint to get user positions
    """
    if request.method != 'GET':
        return JsonResponse({
            "status": "error",
            "error": "Method not allowed"
        }, status=405)
    
    try:
        # Extract user_id from the request (assuming it's set by auth middleware)
        user_id = request.user_data.get('public_id') if hasattr(request, 'user_data') else request.GET.get('user_id')
        
        if not user_id:
            return JsonResponse({
                "status": "error",
                "error": "User ID is required"
            }, status=400)
        
        # Initialize the portfolio service
        portfolio = Portfolio(user_id)
        
        # Get positions
        result = portfolio.get_positions()
        
        return JsonResponse(result, status=200)
        
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "error": str(e)
        }, status=500)

def get_orders(request, *args, **kwargs):
    """
    API endpoint to get user orders
    """
    if request.method != 'GET':
        return JsonResponse({
            "status": "error",
            "error": "Method not allowed"
        }, status=405)
    
    try:
        # Extract user_id from the request (assuming it's set by auth middleware)
        user_id = request.user_data.get('public_id') if hasattr(request, 'user_data') else request.GET.get('user_id')
        
        if not user_id:
            return JsonResponse({
                "status": "error",
                "error": "User ID is required"
            }, status=400)
        
        # Initialize the portfolio service
        portfolio = Portfolio(user_id)
        
        # Get orders
        result = portfolio.get_orders()
        
        return JsonResponse(result, status=200)
        
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "error": str(e)
        }, status=500)

def get_order_trades(request, *args, **kwargs):
    """
    API endpoint to get trades for a specific order
    """
    if request.method != 'GET':
        return JsonResponse({
            "status": "error",
            "error": "Method not allowed"
        }, status=405)
    
    try:
        # Extract user_id from the request (assuming it's set by auth middleware)
        user_id = request.user_data.get('public_id') if hasattr(request, 'user_data') else request.GET.get('user_id')
        
        if not user_id:
            return JsonResponse({
                "status": "error",
                "error": "User ID is required"
            }, status=400)
        
        # Get order_id from query parameters
        order_id = request.GET.get('order_id')
        if not order_id:
            return JsonResponse({
                "status": "error",
                "error": "order_id is required"
            }, status=400)
        
        # Initialize the portfolio service
        portfolio = Portfolio(user_id)
        
        # Get order trades
        result = portfolio.get_order_trades({"order_id": order_id})
        
        return JsonResponse(result, status=200)
        
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "error": str(e)
        }, status=500)

def get_order_history(request, *args, **kwargs):
    """
    API endpoint to get history for a specific order
    """
    if request.method != 'GET':
        return JsonResponse({
            "status": "error",
            "error": "Method not allowed"
        }, status=405)
    
    try:
        # Extract user_id from the request (assuming it's set by auth middleware)
        user_id = request.user_data.get('public_id') if hasattr(request, 'user_data') else request.GET.get('user_id')
        
        if not user_id:
            return JsonResponse({
                "status": "error",
                "error": "User ID is required"
            }, status=400)
        
        # Get order_id from query parameters
        order_id = request.GET.get('order_id')
        if not order_id:
            return JsonResponse({
                "status": "error",
                "error": "order_id is required"
            }, status=400)
        
        # Initialize the portfolio service
        portfolio = Portfolio(user_id)
        
        # Get order history
        result = portfolio.get_order_history({"order_id": order_id})
        
        return JsonResponse(result, status=200)
        
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "error": str(e)
        }, status=500)

def place_order(request, *args, **kwargs):
    """
    API endpoint to place an order
    """
    if request.method != 'POST':
        return JsonResponse({
            "status": "error",
            "error": "Method not allowed"
        }, status=405)
    
    try:
        # Get the request data - handle both JSON and form data
        if request.content_type and 'application/json' in request.content_type:
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({
                    "status": "error",
                    "error": "Invalid JSON in request body"
                }, status=400)
        else:
            # Handle form data
            data = request.POST.dict()
        
        # Extract user_id from the request (assuming it's set by auth middleware)
        user_id = request.user_data.get('public_id') if hasattr(request, 'user_data') else data.get('user_id')
        
        if not user_id:
            return JsonResponse({
                "status": "error",
                "error": "User ID is required"
            }, status=400)
        
        # Initialize the portfolio service
        portfolio = Portfolio(user_id)
        
        # Place order
        result = portfolio.place_order(data)
        
        return JsonResponse(result, status=200)
        
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "error": str(e)
        }, status=500)

def get_available_margin(request, *args, **kwargs):
    """
    API endpoint to get available margin
    """
    if request.method != 'GET':
        return JsonResponse({
            "status": "error",
            "error": "Method not allowed"
        }, status=405)
    
    try:
        # Extract user_id from the request (assuming it's set by auth middleware)
        user_id = request.user_data.get('public_id') if hasattr(request, 'user_data') else request.GET.get('user_id')
        
        if not user_id:
            return JsonResponse({
                "status": "error",
                "error": "User ID is required"
            }, status=400)
        
        # Initialize the portfolio service
        portfolio = Portfolio(user_id)
        
        # Get available margin
        result = portfolio.get_available_margin()
        
        return JsonResponse(result, status=200)
        
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "error": str(e)
        }, status=500)

# Trade endpoints (from TradeView)
def get_quotes(request, *args, **kwargs):
    """
    API endpoint to get quotes for instruments
    """
    if request.method != 'GET':
        return JsonResponse({
            "status": "error",
            "error": "Method not allowed"
        }, status=405)
    
    try:
        # Extract user_id from the request (assuming it's set by auth middleware)
        user_id = request.user_data.get('public_id') if hasattr(request, 'user_data') else request.GET.get('user_id')
        
        if not user_id:
            return JsonResponse({
                "status": "error",
                "error": "User ID is required"
            }, status=400)
        
        # Get query parameters
        symbol = request.GET.get('symbol')
        exchange = request.GET.get('exchange')
        
        # Validate required parameters
        if not symbol or not exchange:
            return JsonResponse({
                "status": "error",
                "error": "Both 'symbol' and 'exchange' parameters are required"
            }, status=400)
        
        # Initialize the trade service
        trade = Trade(user_id)
        
        # Get quotes
        result = trade.get_quotes({
            'symbol': symbol,
            'exchange': exchange
        })
        
        # Check for errors in the result
        if 'error_message' in result:
            log(f"[INTEGRATION_VIEW] Error from Trade.get_quotes: {result['error_message']}", level="error")
            return JsonResponse({
                "status": "error",
                "error": result['error_message']
            }, status=result.get('status_code', 500))
        
        # Log the successful response being sent
        data_keys = list(result['data'].keys())[:3] if isinstance(result.get('data'), dict) else []
        log(f"[INTEGRATION_VIEW] Sending successful response: data_keys_count={len(result.get('data', {}))}, sample_keys={data_keys}")
        
        # Log sample quote data being sent
        if isinstance(result.get('data'), dict) and result['data']:
            first_key = next(iter(result['data']), None)
            if first_key:
                sample_quote = result['data'][first_key]
                log(f"[INTEGRATION_VIEW] SAMPLE QUOTE BEING SENT - {first_key}: last_price={sample_quote.get('last_price')}, volume={sample_quote.get('volume')}")
        
        return JsonResponse({
            "status": "success",
            "data": result['data'],
            "meta": result['meta']
        }, status=200)
        
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "error": str(e)
        }, status=500)

def get_instruments(request, *args, **kwargs):
    """
    API endpoint to get all instruments from Kite API
    """
    if request.method != 'GET':
        return JsonResponse({
            "status": "error",
            "error": "Method not allowed"
        }, status=405)
    
    try:
        # Extract user_id from the request (assuming it's set by auth middleware)
        user_id = request.user_data.get('public_id') if hasattr(request, 'user_data') else request.GET.get('user_id')
        
        if not user_id:
            return JsonResponse({
                "status": "error",
                "error": "User ID is required"
            }, status=400)
        
        # Initialize the instruments provider
        instruments_provider = InstrumentsProvider(user_id)
        
        # Get all instruments
        result = instruments_provider.get_all_instruments()
        
        return JsonResponse(result, status=200)
        
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "error": str(e)
        }, status=500) 
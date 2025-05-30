from trade_management_unit.lib.common.EnvFile import EnvFile
from django.shortcuts import HttpResponse, render
from django.http import JsonResponse
import json
from trade_management_unit.lib.Instruments.Instruments import Instruments
from trade_management_unit.models.Instrument import Instrument
from django.forms.models import model_to_dict
from django.db.models import Q
from django.core.exceptions import FieldError
from datetime import datetime
from django.http import JsonResponse
from django.conf import settings
import requests

def _get_integration_service_url():
    """Helper function to get integration service URL"""
    return getattr(settings, 'INTEGRATION_SERVICE_URL', 'http://localhost:8000/integration_service')

def update_instruments(request, *args, **kwargs):
    query_params = request.GET
    instruments = Instruments()
    instruments.update_instruments()
    return JsonResponse({}, status=200, content_type='application/json')

def get_instruments(request, *args, **kwargs):
    query_params = request.GET
    instruments = Instruments()
    response = instruments.fetch_instruments(query_params)
    return JsonResponse(response, content_type='application/json')

def get_historical_data(request, *args, **kwargs):
    query_params = request.GET
    
    # Extract user_id from the request (assuming it's set by auth middleware)
    user_id = request.user_data.get('public_id') if hasattr(request, 'user_data') else query_params.get('user_id')
    
    try:
        token = int(query_params.get("instrument_id"))
        interval = str(query_params.get("trade_frequency"))
        number_of_candles = int(query_params.get("number_of_candles"))
        date_str = query_params.get("trade_date")
        
        # Get symbol from the database
        symbol = Instrument.objects.get(id=token).trading_symbol
        
        # Make API call to integration service
        api_url = f"{_get_integration_service_url()}/get_historical_data/"
        api_params = {
            'symbol': symbol,
            'token': token,
            'interval': interval,
            'number_of_candles': number_of_candles,
            'user_id': user_id
        }
        
        if date_str:
            api_params['trade_date'] = date_str
        
        response = requests.get(api_url, params=api_params)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                return JsonResponse({
                    'data': data['data'],
                    'meta': data['meta']
                }, content_type='application/json')
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': data.get('error', 'Unknown error from integration service')
                }, status=500, content_type='application/json')
        else:
            return JsonResponse({
                'status': 'error',
                'message': f'Integration service error: {response.text}'
            }, status=response.status_code, content_type='application/json')
            
    except requests.exceptions.RequestException as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Failed to connect to integration service: {str(e)}'
        }, status=500, content_type='application/json')
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }, status=500, content_type='application/json')

from trade_management_unit.lib.common.EnvFile import EnvFile
from django.shortcuts import HttpResponse, render
from django.http import JsonResponse
import json
from trade_management_unit.lib.Instruments.Instruments import Instruments
from trade_management_unit.models.Instrument import Instrument
from django.forms.models import model_to_dict
from django.db.models import Q
from django.core.exceptions import FieldError

def update_instruments(request, *args, **kwargs):
    try:
        # Extract user_id from the request
        user_id = request.user_data.get('public_id') if hasattr(request, 'user_data') else request.GET.get('user_id')
        
        if not user_id:
            return JsonResponse({
                "status": "error",
                "error": "User ID is required"
            }, status=400)
        
        instruments = Instruments()
        instruments.update_instruments(user_id)
        
        return JsonResponse({
            "status": "success",
            "message": "Instruments updated successfully"
        }, status=200)
        
    except Exception as e:
        return JsonResponse({
            "status": "error", 
            "error": str(e)
        }, status=500)

def get_instruments(request, *args, **kwargs):
    query_params = request.GET
    instruments = Instruments()
    response = instruments.fetch_instruments(query_params)
    return JsonResponse(response, content_type='application/json')



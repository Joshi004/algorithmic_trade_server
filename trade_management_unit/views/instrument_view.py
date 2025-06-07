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
    query_params = request.GET
    instruments = Instruments()
    instruments.update_instruments()
    return JsonResponse({}, status=200, content_type='application/json')

def get_instruments(request, *args, **kwargs):
    query_params = request.GET
    instruments = Instruments()
    response = instruments.fetch_instruments(query_params)
    return JsonResponse(response, content_type='application/json')



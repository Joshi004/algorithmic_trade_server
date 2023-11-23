from trade_management_unit.lib.common.EnvFile import EnvFile
from django.shortcuts import HttpResponse, render
from django.http import JsonResponse
import json
from trade_management_unit.lib.Instruments.Instruments import Instruments
from trade_management_unit.lib.Instruments.historical_data.FetchData import FetchData
from trade_management_unit.models.Instrument import Instrument
from django.forms.models import model_to_dict
from django.db.models import Q
from django.core.exceptions import FieldError
from datetime import datetime
from django.http import JsonResponse
from trade_management_unit.lib.Instruments.historical_data.FetchData import FetchData



def update_instruments(request,*args,**kwvrgs):
    query_paramas  =  request.GET
    instruments = Instruments()
    instruments.update_instruments()
    return JsonResponse({},status=200, content_type='application/json')


def get_instruments(request,*args,**kwvrgs):
    query_paramas  =  request.GET
    instruments = Instruments()
    response = instruments.fetch_instruments(query_paramas)
    return JsonResponse(response, content_type='application/json')


def get_historical_data(request,*args,**kwvrgs):
    query_paramas  =  request.GET
    token = int(query_paramas.get("instrument_id"))
    interval = str(query_paramas.get("trade_frequency"))
    number_of_candles = int(query_paramas.get("number_of_candles"))
    date_str = (query_paramas.get("trade_date"))
    symbol = Instrument.objects.get(id=token).trading_symbol
    response = FetchData().fetch_historical_data_for_client(symbol, token, interval, number_of_candles,date_str)
    return JsonResponse(response, content_type='application/json')

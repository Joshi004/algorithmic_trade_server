from django.shortcuts import HttpResponse, render
from django.http import JsonResponse
import json
from django.core import serializers
from trade_management_unit.lib.common.Communicator import Communicator 
from trade_management_unit.lib.Trade.trade import Trade


def get_quotes(request,*args,**kwvrgs):
    query_paramas  =  request.GET
    trade = Trade()
    response = trade.get_quotes(query_paramas)
    return JsonResponse(response,status=200, content_type='application/json')

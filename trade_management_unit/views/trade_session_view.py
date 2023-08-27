from django.shortcuts import HttpResponse, render
from django.http import JsonResponse
import json
from django.core import serializers
from trade_management_unit.lib.common.Communicator import Communicator 
from trade_management_unit.lib.TradeSession.trade import Trade


def set_price(request,*args,**kwvrgs):
    print("Set Price")
    body  =  request.body.decode("utf-8")
    json_data = json.loads(body)  # Parse the JSON data 
    trade = Trade()
    communicator = Communicator()
    instruments  = trade.get_instruments()
    print("Sending Instruments to Communicator",instruments)
    communicator.send_data_to_channel_layer(instruments,"trade_group") 
    return JsonResponse(instruments, content_type='application/json')

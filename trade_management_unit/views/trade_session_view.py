from django.shortcuts import HttpResponse, render
from django.http import JsonResponse
import json
from django.core import serializers
from trade_management_unit.lib.common.Communicator import Communicator 


def set_price(request,*args,**kwvrgs):
    print("Set Price")
    body  =  request.body.decode("utf-8")
    json_data = json.loads(body)  # Parse the JSON data 
    communicator = Communicator()
    print("Sending COntrol to Communicator",json_data)
    communicator.send_data_to_channel_layer(json_data,"random_number_channel") 
    return HttpResponse({"qs_json":"recieved"}, content_type='application/json')

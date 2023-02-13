from django.shortcuts import render
from django.http import JsonResponse
import json
from  trade_management_unit.models.Stock import Stock
from django.forms.models import model_to_dict



def api_home(request, *args, **kwvrgs):
    # request  = HTTpRequest Django
    # request.body
    print(request.GET)
    # data = {}
    # try:
    #     data  =  json.loads(request.body)
    # except:
    #     data["params"] = dict(request.GET)
    #     data['headers'] = dict(request.headers)
    #     print("Some Error laoding JSON")
    # print(data)
    # data["my_key"] = "Value001"
    data = {}
    model_data = Stock.objects.all().order_by("?").first()
    data = model_to_dict(model_data,fields=["title","id"])
    return JsonResponse(data)
# Create your views here.

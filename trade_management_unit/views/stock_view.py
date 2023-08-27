from django.shortcuts import HttpResponse, render
from django.http import JsonResponse
import json
from trade_management_unit.models.Stock import Stock
from trade_management_unit.lib.stock.update_stocks import UpdateStock
from django.forms.models import model_to_dict
from django.db.models import Q
from django.core import serializers
from django.http import JsonResponse





def fetch_and_update_stocks(request, *args, **kwvrgs):
    print(request.GET)
    print("Updating Stocks in controller")
    updater = UpdateStock()
    updater.update()
    data = {"status":200}
    # model_data = Stock.objects.all().order_by("?").first()
    # data = model_to_dict(model_data,fields=["title","id"])
    return JsonResponse(data)


def get_stocks_list(request,*args,**kwvrgs):
    query_paramas  =  request.GET
    search_param = query_paramas["search"] if "search" in query_paramas else "" # COnditional Parameter
    query_set = Stock.objects.filter(Q(nse_symbol__icontains=search_param) | Q(name__icontains=search_param))
    qs_json = serializers.serialize('json', query_set)
    return HttpResponse(qs_json, content_type='application/json')


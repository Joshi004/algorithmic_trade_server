from trade_management_unit.lib.common.EnvFile import EnvFile
from django.shortcuts import HttpResponse, render
from django.http import JsonResponse
import json
from trade_management_unit.lib.Instruments.Instruments import Instruments
from django.forms.models import model_to_dict
from django.db.models import Q
from django.core import serializers
from django.http import JsonResponse





def update_instruments(request,*args,**kwvrgs):
    query_paramas  =  request.GET
    instruments = Instruments(query_paramas)
    instruments.update_instruments()



def get_instruments(request,*args,**kwvrgs):
    query_paramas  =  request.GET
    search_param = query_paramas["search"] if "search" in query_paramas else "" # COnditional Parameter
    query_set = Instrument.objects.filter(Q(nse_symbol__icontains=search_param) | Q(name__icontains=search_param))
    qs_json = serializers.serialize('json', query_set)
    return HttpResponse(qs_json, content_type='application/json')


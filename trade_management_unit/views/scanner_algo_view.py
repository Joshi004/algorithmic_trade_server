from django.http import JsonResponse
from trade_management_unit.lib.Algorithms.ScannerAlgos.ScannerAlgoFactory import ScannerAlgoFactory
from trade_management_unit.lib.Algorithms.ScannerAlgos.UDTS.UDTSHelper import UdtsHelper

def get_eligible_instruments(request, *args, **kwargs):
    query_params = request.GET
    scanner_algo_name = query_params.get('algo_name', 'udts')
    scanner_algo = ScannerAlgoFactory().get_scanner(scanner_algo_name)
    response = scanner_algo.get_eligible_instruments() 
    return JsonResponse(response, status=200, content_type='application/json')


def get_udts_eligibility(request, *args, **kwargs):
    query_params = request.GET
    scanner_algo_name = query_params.get('algo_name', 'udts')
    symbol = query_params.get('symbol')
    frequency = query_params.get('trade_frequency')
    scanner_algo = ScannerAlgoFactory().get_scanner(scanner_algo_name,"slto",frequency)
    response = scanner_algo.get_udts_eligibility(symbol,frequency)
    return JsonResponse(response, status=200, content_type='application/json')


def get_udts_redcord(request, *args, **kwargs):
    query_params = request.GET
    trade_id = query_params.get('trade_id')
    response = UdtsHelper().fetch_udts_record_for_trade(trade_id)
    return JsonResponse(response, status=200, content_type='application/json')


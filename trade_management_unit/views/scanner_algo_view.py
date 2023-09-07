from django.http import JsonResponse
from trade_management_unit.lib.Algorithms.ScannerAlgos.ScannerAlgoFactory import ScannerAlgoFactory

def get_eligible_instruments(request, *args, **kwargs):
    query_params = request.GET
    scanner_algo_name = query_params.get('algo_name', 'udts')
    scanner_algo = ScannerAlgoFactory().get_scanner(scanner_algo_name)
    response = scanner_algo.get_eligible_instruments()
    
    return JsonResponse(response, status=200, content_type='application/json')
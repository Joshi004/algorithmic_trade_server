from trade_management_unit.lib.Algorithms.ScannerAlgos.UDTS.UDTSScanner import UDTSScanner
class ScannerAlgoFactory:
    def __init__(slef):
        pass

    def get_scanner(self,sanning_algo_name,tracking_algo_name,trade_freq):
        if (sanning_algo_name == "udts"):
            return UDTSScanner(trade_freq,tracking_algo_name)
        else:
            return None
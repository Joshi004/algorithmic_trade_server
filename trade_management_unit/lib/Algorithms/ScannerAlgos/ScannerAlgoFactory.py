from trade_management_unit.lib.Algorithms.ScannerAlgos.UDTS.UDTSScanner import UDTSScanner
class ScannerAlgoFactory:
    def __init__(slef):
        pass

    def get_scanner(self,algo_name):
        if (algo_name == "udts"):
            return UDTSScanner()
        else:
            return None
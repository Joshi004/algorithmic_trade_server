from scanning_service.lib.Algorithms.ScannerAlgos.UDTS.UDTSScanner import UDTSScanner

class ScannerAlgoFactory:
    def __init__(self):
        pass

    def get_scanner(self, scanning_algo_name):
        """
        Get scanner instance based on algorithm name with minimal parameters.
        Returns a bare instance that needs to be configured before use.
        
        Args:
            scanning_algo_name: Name of the scanning algorithm (e.g., "udts")
            
        Returns:
            Scanner instance (unconfigured) or None if algorithm not found
        """
        if scanning_algo_name == "udts":
            return UDTSScanner()
        else:
            return None
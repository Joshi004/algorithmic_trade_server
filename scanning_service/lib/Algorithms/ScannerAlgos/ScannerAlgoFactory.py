from scanning_service.lib.Algorithms.ScannerAlgos.UDTS.UDTSScanner import UDTSScanner

class ScannerAlgoFactory:
    def __init__(self):
        pass

    def get_scanner(self, scanning_algo_name, frequency):
        """
        Get scanner instance based on algorithm name and frequency.
        Returns a singleton instance for the algorithm+frequency combination.
        
        Args:
            scanning_algo_name: Name of the scanning algorithm (e.g., "udts")
            frequency: Trading frequency (e.g., "5-minute", "10-minute")
            
        Returns:
            Scanner singleton instance for the algorithm+frequency combination or None if algorithm not found
        """
        if scanning_algo_name == "udts":
            return UDTSScanner(scanning_algo_name, frequency)
        else:
            return None
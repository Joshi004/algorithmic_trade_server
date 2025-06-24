from scanning_service.lib.Algorithms.ScannerAlgos.UDTS.UDTSScanner import UDTSScanner

class ScannerAlgoFactory:
    def __init__(self):
        # Algorithm mapping is now based on algorithm names
        pass

    def get_scanner(self, scanning_algo_name, frequency):
        """
        Get scanner instance based on algorithm name and frequency.
        Returns a singleton instance for the algorithm+frequency combination.
        
        Args:
            scanning_algo_name: Name of the scanning algorithm (e.g., "UDTS")
            frequency: Trading frequency (e.g., "5-minute", "10-minute")
            
        Returns:
            Scanner singleton instance for the algorithm+frequency combination or None if algorithm not found
        """
        # Add debug logging
        from scanning_service.lib.utils.logger import log
        log(f"ScannerAlgoFactory: Creating scanner for algorithm '{scanning_algo_name}', frequency='{frequency}'")
        
        if not scanning_algo_name:
            return None
        
        # Map algorithm names to scanner classes
        if scanning_algo_name == "UDTS":
            log(f"ScannerAlgoFactory: Creating UDTSScanner with algorithm_name='{scanning_algo_name}', frequency='{frequency}'")
            return UDTSScanner(scanning_algo_name, frequency)
        # Future algorithms can be added here:
        # elif scanning_algo_name == "RSI_DIVERGENCE":
        #     return RSIDivergenceScanner(scanning_algo_name, frequency)
        # elif scanning_algo_name == "BREAKOUT_SCANNER":
        #     return BreakoutScanner(scanning_algo_name, frequency)
        # elif scanning_algo_name == "MOMENTUM_SURGE":
        #     return MomentumSurgeScanner(scanning_algo_name, frequency)
        else:
            return None
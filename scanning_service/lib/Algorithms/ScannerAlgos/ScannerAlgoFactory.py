from scanning_service.lib.Algorithms.ScannerAlgos.UDTS.UDTSScanner import UDTSScanner
from trade_management_unit.models.ScanningAlgorithm import ScanningAlgorithm

class ScannerAlgoFactory:
    def __init__(self):
        # Algorithm mapping is now fetched from database dynamically
        pass

    def get_scanner(self, scanning_algo_id, frequency):
        """
        Get scanner instance based on algorithm ID and frequency.
        Returns a singleton instance for the algorithm+frequency combination.
        
        Args:
            scanning_algo_id: ID of the scanning algorithm (e.g., 1 for UDTS)
            frequency: Trading frequency (e.g., "5-minute", "10-minute")
            
        Returns:
            Scanner singleton instance for the algorithm+frequency combination or None if algorithm not found
        """
        # Get algorithm name from database
        algorithm_name = ScanningAlgorithm.get_name_by_id(scanning_algo_id)
        
        # Add debug logging
        from scanning_service.lib.utils.logger import log
        log(f"ScannerAlgoFactory: Retrieved algorithm name '{algorithm_name}' for ID {scanning_algo_id}")
        
        if not algorithm_name:
            return None
        
        # Map algorithm names to scanner classes
        if algorithm_name == "UDTS":
            log(f"ScannerAlgoFactory: Creating UDTSScanner with algorithm_name='{algorithm_name}', frequency='{frequency}'")
            return UDTSScanner(algorithm_name, frequency)
        # Future algorithms can be added here:
        # elif algorithm_name == "RSI_DIVERGENCE":
        #     return RSIDivergenceScanner(algorithm_name, frequency)
        # elif algorithm_name == "BREAKOUT_SCANNER":
        #     return BreakoutScanner(algorithm_name, frequency)
        # elif algorithm_name == "MOMENTUM_SURGE":
        #     return MomentumSurgeScanner(algorithm_name, frequency)
        else:
            return None
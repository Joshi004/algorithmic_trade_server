from scanning_service.lib.Algorithms.ScannerAlgos.UDTS.UDTSScanner import UDTSScanner

class ScannerAlgoFactory:
    def __init__(self):
        # Mapping of algorithm IDs to algorithm types
        self.algorithm_map = {
            1: "udts",  # UDTS algorithm
            # Get this  from Db LAter may be cach as well 
            # 2: "rsi_divergence",
            # 3: "breakout_scanner", 
            # 4: "momentum_surge"
        }

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
        # Get algorithm type from ID
        algorithm_type = self.algorithm_map.get(scanning_algo_id)
        
        if algorithm_type == "udts":
            return UDTSScanner(algorithm_type, frequency)
        else:
            return None
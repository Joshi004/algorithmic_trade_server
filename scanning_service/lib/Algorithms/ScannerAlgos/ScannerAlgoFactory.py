from scanning_service.lib.Algorithms.ScannerAlgos.UDTS.UDTSScanner import UDTSScanner
from scanning_service.lib.data_providers import IntegrationServiceProvider, TMUServiceProvider

class ScannerAlgoFactory:
    def __init__(self):
        pass

    def get_scanner(self, scanning_algo_name, tracking_algo_name, trade_freq, user_id=None, 
                   integration_provider=None, tmu_provider=None, trade_session_id=None):
        """
        Get scanner instance based on algorithm name.
        
        Args:
            scanning_algo_name: Name of the scanning algorithm (e.g., "udts")
            tracking_algo_name: Name of the tracking algorithm
            trade_freq: Trading frequency
            user_id: User ID for the scanner
            integration_provider: Integration service provider instance (optional)
            tmu_provider: TMU service provider instance (optional)
            trade_session_id: Trade session ID for event publishing
            
        Returns:
            Scanner instance or None if algorithm not found
        """
        if scanning_algo_name == "udts":
            return UDTSScanner(
                trade_freq, 
                user_id, 
                integration_provider, 
                tmu_provider,
                trade_session_id
            )
        else:
            return None
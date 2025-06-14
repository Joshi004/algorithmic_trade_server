from scanning_service.lib.utils.logger import log
from scanning_service.lib.Algorithms.ScannerAlgos.UDTS.CandleChart import CandleChart
from scanning_service.lib.Algorithms.ScannerAlgos.ScannerSingletonMeta import ScannerSingletonMeta
from scanning_service.lib.Algorithms.ScannerAlgos.BaseScannerInterface import BaseScannerInterface
from scanning_service.constants import (
    DEFAULT_EXCHANGE,
    FREQUENCY_STEPS,
    NUM_CANDLES_FOR_TREND_ANALYSIS,
    SCOPE_COLLECTION_FREQ_INDEX,
    MINIMUM_REWARD_RISK_RATIO,
    MARKET_OPEN_TIME,
    MARKET_CLOSE_TIME,
    TRADE_THRESHHOLD_PER_MINUTE,
    Trends,
    OrderType
)
import pandas as pd
import threading
from scanning_service.lib.utils.common import current_ist
from scanning_service.lib.data_providers import IntegrationServiceProvider, TMUServiceProvider
from scanning_service.lib.state_management import StateManagerFactory, StateManagementConfig


class UDTSScanner(BaseScannerInterface, metaclass=ScannerSingletonMeta):
    def __init__(self, algorithm_type, frequency):
        """
        Initialize UDTS scanner for specific algorithm type and frequency.
        Called by singleton metaclass with algorithm_type and frequency parameters.
        
        Args:
            algorithm_type: Type of algorithm (should be "udts")
            frequency: Trading frequency (e.g., "5-minute", "10-minute")
        """
        # Initialize base class
        super().__init__()
        
        # Store algorithm type and frequency for this singleton instance
        self.algorithm_type = algorithm_type
        self.frequency = frequency
        
        # Initialize scanner-specific attributes
        self.integration_provider = None
        self.tmu_provider = None
        self.data_provider = None
        self.event_publisher = None
        
        # Thread management
        self._scanner_thread = None
        self._stop_event = threading.Event()
        self._is_running = False
        
        # State management
        self.state_manager = None
        self.progress_update_interval = 10  # Update state every 10 instruments (configurable)
        
        log(f"Initialized UDTSScanner singleton for {algorithm_type} algorithm with {frequency} frequency")
    
    def configure(self, trade_freq: str, **kwargs):
        """
        Configure the UDTS scanner with required parameters and dependencies.
        
        Note: user_id and trade_session_id are not stored as instance state
        since this scanner is now a frequency-based singleton.
        
        Args:
            trade_freq: Trading frequency (e.g., "5minute")
            **kwargs: Additional configuration (integration_provider, tmu_provider, user_id, trade_session_id)
        """
        # Call parent configure (handles event publisher setup)
        super().configure(trade_freq, **kwargs)
        
        # Extract user_id from kwargs for provider initialization
        user_id = kwargs.get('user_id')
        
        # Use provided providers or create default ones
        self.integration_provider = kwargs.get('integration_provider') or IntegrationServiceProvider(user_id) if user_id else None
        self.tmu_provider = kwargs.get('tmu_provider') or TMUServiceProvider(user_id) if user_id else None
        
        # Keep data_provider for backward compatibility (points to integration provider)
        self.data_provider = self.integration_provider
        
        # Initialize state manager for this scanner
        self._initialize_state_manager(**kwargs)
        
        log(f"UDTS Scanner configured for frequency: {trade_freq}")

    def _initialize_state_manager(self, **kwargs):
        """
        Initialize state manager for this scanner.
        
        Args:
            **kwargs: Configuration parameters including ttl_hours, progress_update_interval
        """
        try:
            # Extract configuration parameters
            ttl_hours = kwargs.get('ttl_hours')  # Uses config default if None
            self.progress_update_interval = StateManagementConfig.get_progress_update_interval(
                kwargs.get('progress_update_interval')
            )
            
            # Create state manager using factory
            self.state_manager = StateManagerFactory.create_state_manager(
                scanner_type=self.algorithm_type,
                algorithm_type=self.algorithm_type,
                frequency=self.frequency,
                ttl_hours=ttl_hours
            )
            
            if self.state_manager:
                log(f"State manager initialized for {self.algorithm_type}_{self.frequency}")
            else:
                log(f"State management not available for {self.algorithm_type} scanner", level="warning")
                
        except Exception as e:
            log(f"Error initializing state manager: {str(e)}", level="error")
            self.state_manager = None

    def resume_or_start_scanning(self, all_instruments):
        """
        Determine starting index for scanning based on saved state.
        If valid state exists and instruments match, resume from last position.
        Otherwise, start from beginning.
        
        Args:
            all_instruments: List of instruments to scan
            
        Returns:
            int: Starting index for scanning
        """
        if not self.state_manager:
            log("No state manager available, starting from beginning")
            return 0
        
        try:
            # Get saved progress
            progress = self.state_manager.get_progress()
            
            if not progress:
                log("No saved progress found, starting from beginning")
                return 0
            
            # Validate progress is still relevant
            saved_total = progress.get('total_instruments', 0)
            current_total = len(all_instruments)
            
            if saved_total != current_total:
                log(f"Instrument count changed: saved={saved_total}, current={current_total}. Starting fresh.")
                return 0
            
            # Check if progress is recent enough
            from datetime import timedelta
            last_update = progress.get('last_update_time')
            max_age = timedelta(hours=StateManagementConfig.MAX_STATE_AGE_HOURS)
            if last_update and (current_ist() - last_update) > max_age:
                log(f"Saved progress is too old (>{StateManagementConfig.MAX_STATE_AGE_HOURS}h), starting fresh")
                return 0
            
            saved_index = progress.get('current_index', 0)
            last_symbol = progress.get('last_processed_symbol', '')
            
            # Validate the symbol at saved index matches
            if saved_index < len(all_instruments):
                expected_symbol = all_instruments[saved_index].get('trading_symbol', '')
                if last_symbol == expected_symbol:
                    log(f"Resuming scanning from index {saved_index + 1} after symbol '{last_symbol}'")
                    return saved_index + 1
            
            log("Saved progress validation failed, starting from beginning")
            return 0
            
        except Exception as e:
            log(f"Error checking saved progress: {str(e)}", level="error")
            return 0
    
    def _get_current_cycle(self):
        """
        Get current scan cycle number from state or start at 1.
        
        Returns:
            int: Current scan cycle number
        """
        if not self.state_manager:
            return 1
            
        try:
            progress = self.state_manager.get_progress()
            if progress:
                return progress.get('scan_cycle', 1)
        except Exception as e:
            log(f"Error getting current cycle: {str(e)}", level="error")
        
        return 1

    def _save_scanning_progress(self, current_index, last_processed_symbol):
        """
        Save current scanning progress to Redis state.
        
        Args:
            current_index: Current index in the instrument list
            last_processed_symbol: Symbol of the last processed instrument
        """
        if not self.state_manager:
            return
            
        try:
            self.state_manager.save_progress(
                current_index=current_index,
                total_instruments=len(self.all_instruments) if hasattr(self, 'all_instruments') else 0,
                last_processed_symbol=last_processed_symbol,
                scan_cycle=getattr(self, 'scan_cycle', 1),
                cycle_start_time=getattr(self, 'cycle_start_time', current_ist())
            )
        except Exception as e:
            log(f"Error saving scanning progress: {str(e)}", level="error")



    def fetch_instrument_tokens_and_start_tracking(self, user_id, trade_session_id, dummy):
        self._ensure_configured()
        
        instrument_list = self.fetch_instruments()
        self.scan_instruments(instrument_list, user_id, trade_session_id, dummy)

    def scan_in_separate_thread(self, all_instruments):
        self._ensure_configured()
        
        # Resume or start fresh
        start_index = self.resume_or_start_scanning(all_instruments)
        
        self._is_running = True
        self.all_instruments = all_instruments
        self.scan_cycle = self._get_current_cycle()
        self.cycle_start_time = current_ist()
        
        log(f'Scanning started for {len(all_instruments)} instruments from index {start_index}')
        
        while not self._stop_event.is_set():
            scan_start_time = current_ist()
            eligible_instrument_counter = 0
            
            # Process instruments from resume point
            for idx in range(start_index, len(all_instruments)):
                if self._stop_event.is_set():
                    break
                    
                instrument = all_instruments[idx]
                symbol = instrument["trading_symbol"]
                token = instrument["instrument_token"]
                log(f'Scanning {symbol} now (index {idx + 1}/{len(all_instruments)})')
                
                is_eligible, eligibility_obj = self.is_eligible(symbol)
                
                if is_eligible:
                    instrument_id = token
                    eligible_instrument_counter += 1
                    log(f"found next eligible instrument -- {eligible_instrument_counter} {symbol}")
                    symbol_data_points = eligibility_obj[self.trade_frequency]["chart"]
                    
                    # Prepare raw instrument data
                    raw_instrument_data = {
                        "instrument_id": instrument_id,
                        "trading_symbol": symbol,
                        "support_price": float(symbol_data_points.trading_pair["support"]),
                        "resistance_price": float(symbol_data_points.trading_pair["resistance"]),
                        "required_action": self.__get_required_actions__(eligibility_obj["effective_trend"]),
                        "market_price": float(symbol_data_points.market_price)
                    }
                    
                    # Format using base class method to ensure standardization
                    instrument_data = self.format_eligible_instrument(raw_instrument_data)
                    
                    # This will now publish to ALL active trade sessions using this scanner using parent
                    self.publish_eligible_instruments([instrument_data])
                else:
                    log(f'Not Eligible {eligibility_obj["message"]}')
                
                # Update state periodically (every N instruments)
                if self.state_manager and (idx + 1) % self.progress_update_interval == 0:
                    self._save_scanning_progress(idx, symbol)
                    
            # Cycle completed - update state and prepare for next cycle
            if not self._stop_event.is_set():
                scan_end_time = current_ist()
                scan_duration = (scan_end_time - scan_start_time).total_seconds()
                
                # Save final state for this cycle
                if self.state_manager:
                    final_index = len(all_instruments) - 1
                    final_symbol = all_instruments[final_index]["trading_symbol"] if all_instruments else ""
                    self._save_scanning_progress(final_index, final_symbol)
                
                self.scan_cycle += 1
                
                log(f"Scan cycle {self.scan_cycle - 1} completed - Duration: {scan_duration}s, Found: {eligible_instrument_counter}")
                log(f'Last scan total time taken {scan_duration} seconds')
                
                # Reset start_index for next cycle
                start_index = 0
                
                # Use wait instead of sleep to be interruptible
                self._stop_event.wait(timeout=30)
        
        # Scanner stopped
        self._is_running = False
        log(f"Scanner thread for {self.trade_frequency} stopped after {self.scan_cycle} cycles")


    def is_eligible(self, symbol):
        """
        Check if a trading symbol is eligible for UDTS strategy based on volume, trend analysis, and reward-risk ratio.
        
        Args:
            symbol: Trading symbol to analyze (e.g., "RELIANCE")
            
        Returns:
            tuple: (is_eligible: bool, eligibility_data: dict)
        """
        self._ensure_configured()
        
        # Initialize eligibility tracking object with default message
        eligibility_data = {"message": str(symbol) + " : Eligible"}
        
        # Fetch real-time quote data for the symbol
        quote_response = self.data_provider.get_quotes(symbol, DEFAULT_EXCHANGE)
        quotes_data = quote_response.get("data", {})
        
        # Create quote key in expected format (EXCHANGE:SYMBOL)
        quote_key = DEFAULT_EXCHANGE + ":" + symbol.upper()
        
        # Validate that quote data exists for this symbol
        if quote_key not in quotes_data:
            eligibility_data["message"] = symbol + " : No Data Fetched from quotes"
            return False, eligibility_data
            
        # Extract instrument token and quote details
        instrument_token = quotes_data[quote_key]["instrument_token"]
        current_quote_data = quotes_data[quote_key]
        
        # Get trading frequency configuration
        current_trade_frequency = self.trade_frequency
        frequency_steps = FREQUENCY_STEPS[current_trade_frequency]
        required_candles_count = NUM_CANDLES_FOR_TREND_ANALYSIS
        
        # Check if volume meets minimum trading threshold
        is_volume_sufficient = self.get_volume_eligibility(current_quote_data)
        if not is_volume_sufficient:
            eligibility_data["message"] = symbol + " : Volume not eligible"
            return False, eligibility_data
        
        # Analyze trends across multiple timeframes
        for frequency_index in range(0, len(frequency_steps)):
            current_frequency = frequency_steps[frequency_index]
            eligibility_data[current_frequency] = {}
            
            # Fetch historical candle data for this timeframe
            eligibility_data[current_frequency]["data"] = self.data_provider.fetch_historical_candle_data_from_kite(
                symbol, instrument_token, frequency_steps[frequency_index], required_candles_count
            )
            
            # Validate sufficient historical data exists
            historical_candles = eligibility_data[current_frequency]["data"]
            if len(historical_candles) < NUM_CANDLES_FOR_TREND_ANALYSIS:
                eligibility_data["message"] = symbol + " : Not Enough Candles For " + str(current_frequency)
                return False, eligibility_data
                
            # Create candle chart for trend analysis
            eligibility_data[current_frequency]["chart"] = CandleChart(
                symbol, 
                instrument_token, 
                current_quote_data["last_price"], 
                current_quote_data["volume"], 
                current_quote_data["last_quantity"], 
                frequency_steps[frequency_index], 
                eligibility_data[current_frequency]["data"]
            )
            
            # Calculate trend direction and key price levels
            eligibility_data[current_frequency]["chart"].set_trend_and_deflection_points()
        
        # Use center timeframe element to establish price scope for normalization
        scope_reference_chart = eligibility_data[frequency_steps[SCOPE_COLLECTION_FREQ_INDEX]]["chart"]
        price_deflection_scope = self.__get_deflection_points_scope(scope_reference_chart)
        
        # Normalize deflection points and calculate trading levels for primary timeframe
        primary_timeframe_chart = eligibility_data[current_trade_frequency]["chart"]
        primary_timeframe_chart.normalise_deflection_points(price_deflection_scope)
        primary_timeframe_chart.set_trading_levels_and_ratios()
        
        # Determine overall trend consensus across timeframes
        consensus_trend = self.__get_effective_trend(eligibility_data)
        eligibility_data["effective_trend"] = consensus_trend

        # Validate that valid trading pairs exist
        valid_trading_pairs = primary_timeframe_chart.valid_pairs
        if not valid_trading_pairs or len(valid_trading_pairs) < 1:
            eligibility_data["message"] = symbol + " : No Valid Trading pairs Present"
            return False, eligibility_data

        # Extract reward-to-risk ratio for final eligibility check
        trading_pair_data = primary_timeframe_chart.trading_pair
        current_reward_risk_ratio = trading_pair_data.get("reward_risk_ratio", 0)
        
        # Update eligibility message with trend and ratio information
        eligibility_data["message"] = f"{symbol} : {consensus_trend.value} , Reward:Risk - {current_reward_risk_ratio}"
        
        # Final eligibility decision based on minimum reward-risk threshold
        if current_reward_risk_ratio > MINIMUM_REWARD_RISK_RATIO:
            return True, eligibility_data

        return False, eligibility_data

    def get_volume_eligibility(self, quote):
        self.volume = quote["volume"]
        
        # Define market open and close times
        market_open_time = current_ist().replace(**MARKET_OPEN_TIME)
        market_close_time = current_ist().replace(**MARKET_CLOSE_TIME)
        
        # Get current time
        current_time = current_ist()
        
        # Calculate total minutes from market open to current time or total trade duration
        if current_time > market_open_time:
            # If current time is before market open, consider total trade duration of a day
            total_minutes = int(( market_open_time - market_close_time).total_seconds() / 60)
        elif current_time < market_close_time:
            # If current time is after market close, consider end time as market close
            current_time = market_close_time
            total_minutes = int((market_open_time - current_time).total_seconds() / 60)
        else:
            # If current time is within trading hours
            total_minutes = int((market_open_time - current_time).total_seconds() / 60)
        
        # Calculate volume per minute
        volume_per_minute = self.volume / total_minutes
        trade_amount_per_minute = quote["last_price"]*volume_per_minute 
        # Check if volume per minute is greater than threshold
        log(f'Volume Analysis trade_amount_per_minute {trade_amount_per_minute} TRADE_THRESHHOLD_PER_MINUTE {TRADE_THRESHHOLD_PER_MINUTE}')
        if trade_amount_per_minute > TRADE_THRESHHOLD_PER_MINUTE:
            return True
        else:
            return False
            
            
    def get_udts_eligibility(self,symbol,trade_freq):
        self._ensure_configured()
        
        print("get token and send hereh !!! nOt Working !!!!")
        is_tradable,eligibility_obj =  self.is_eligible(symbol)
        result = eligibility_obj[trade_freq]["chart"]
        response_obj = {
            "data":{
            "price_list" : result.price_list,
            "trend":result.trend.value,
            "effective_trend" : eligibility_obj["effective_trend"].value,
            "deflection_points":result.deflection_points,
            "trading_pair":result.trading_pair,
            "average_candle_span":result.average_candle_span,
            "rounding_factor":result.rounding_factor,
            "valid_pairs":result.valid_pairs,
            "market_price":result.market_price,
            "up_scope":result.up_scope,
            "down_scope":result.down_scope,
            },
            "meta":{
            "interval":result.interval,
            "symbol":result.symbol,
            }
        }
        return response_obj

    def stop_scanning(self):
        """Stop the scanner thread gracefully."""
        log(f"Stopping scanner for trade frequency: {self.trade_frequency}")
        self._stop_event.set()
        
        if self._scanner_thread and self._scanner_thread.is_alive():
            log("Waiting for scanner thread to finish...")
            self._scanner_thread.join(timeout=5)
            
            if self._scanner_thread.is_alive():
                log("Scanner thread did not stop gracefully within timeout", level="warning")
            else:
                log("Scanner thread stopped successfully")
        
        self._is_running = False
    
    def is_running(self):
        """Check if scanner is currently running."""
        return self._is_running and self._scanner_thread and self._scanner_thread.is_alive()

    def fetch_instruments(self):
        self._ensure_configured()
        
        search_params = {"exchange": "NSE", "segment": "NSE", "instrument_type": "EQ", "page_length": 5000}
        
        # Fetch Instruments using TMU service provider
        log("Fetching instruments from TMU service")
        result = self.tmu_provider.fetch_instruments(search_params)
        
        if "error" in result.get("meta", {}):
            log(f"Error fetching instruments: {result['meta']['error']}", level="error")
            return []
        
        instruments = result.get("data", [])
        log(f"Successfully fetched {len(instruments)} instruments from TMU")
        return instruments

    def scan_instruments(self, all_instruments, user_id, trade_session_id, dummy):
        self._ensure_configured()
        
        # Store the thread reference
        thread_name = f"scanner_thread_udts_{self.trade_frequency}"
        self._scanner_thread = threading.Thread(
            target=self.scan_in_separate_thread,
            args=(all_instruments,),
            name=thread_name
        )
        self._scanner_thread.daemon = True
        self._scanner_thread.start()
        log(f"Started scanner thread: {thread_name}")

    def __str__(self):
        identifier = f"{self.algorithm_type}__{self.frequency}"
        return identifier

   
    def __get_required_actions__(self, effective_trend):
        required_action = None
        if effective_trend == Trends.UPTREND:
            required_action = OrderType.BUY.value
        elif effective_trend == Trends.DOWNTREND:
            required_action = OrderType.SELL.value
        else:
            required_action = None
        return required_action


    def __get_effective_trend(self,eligibility_obj):
        trends = set()
        for frequency in eligibility_obj:
            if frequency == "message":
                continue
            chart = eligibility_obj[frequency]["chart"]
            trends.add(chart.trend)
        effective_ternd = trends.pop() if len(trends) == 1 else Trends.SIDETREND
        return effective_ternd
    
    def __get_deflection_points_scope(self,base_chart):
        price_list = base_chart.price_list
        price_list_df = pd.DataFrame(price_list)
        price_list_df["diff"] = price_list_df["high"] - price_list_df["low"]
        average_candle_span = price_list_df["diff"].mean()
        return float(average_candle_span)

  
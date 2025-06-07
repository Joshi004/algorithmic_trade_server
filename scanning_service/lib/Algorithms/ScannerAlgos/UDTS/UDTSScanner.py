import time as tm
from scanning_service.lib.utils.logger import log
from scanning_service.lib.Algorithms.ScannerAlgos.UDTS.CandleChart import CandleChart
from scanning_service.lib.Algorithms.ScannerAlgos.ScannerSingletonMeta import ScannerSingletonMeta
from scanning_service.lib.Algorithms.ScannerAlgos.BaseScannerInterface import BaseScannerInterface
from scanning_service.constants import *
import pandas as pd
import threading
from scanning_service.lib.utils.common import current_ist
from scanning_service.lib.data_providers import IntegrationServiceProvider, TMUServiceProvider
from scanning_service.lib.utils.redis import get_scanning_event_publisher
import requests
from django.conf import settings


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
        # Call parent configure
        super().configure(trade_freq, **kwargs)
        
        # Extract user_id from kwargs for provider initialization
        user_id = kwargs.get('user_id')
        
        # Use provided providers or create default ones
        self.integration_provider = kwargs.get('integration_provider') or IntegrationServiceProvider(user_id) if user_id else None
        self.tmu_provider = kwargs.get('tmu_provider') or TMUServiceProvider(user_id) if user_id else None
        
        # Keep data_provider for backward compatibility (points to integration provider)
        self.data_provider = self.integration_provider
        
        # Event publisher
        self.event_publisher = get_scanning_event_publisher()
        
        log(f"UDTS Scanner configured for frequency: {trade_freq}")
     
    def __str__(self):
        identifier = f"{self.algorithm_type}__{self.frequency}"
        return identifier

    def scan_in_separate_thread(self, all_instruments, user_id, trade_session_id, dummy):
        self._ensure_configured()
        
        tm.sleep(4) # let Trade session be created
        counter = 0
        self._is_running = True
        
        # Publish scanner started status
        self.event_publisher.publish_scanner_status(
            user_id=user_id,
            trade_session_id=trade_session_id,
            scanner_type="udts",
            status="started",
            details={"trade_frequency": self.trade_frequency, "instruments_count": len(all_instruments)}
        )
        
        while not self._stop_event.is_set():
            counter += 1
            eligible_instruments = []
            instrument_counter = 0
            eligible_instrument_counter = 0
            scan_start_time = current_ist()
            
            for instrument in all_instruments:
                # Check for stop event during scanning
                if self._stop_event.is_set():
                    break
                    
                instrument_counter += 1
                symbol = instrument["trading_symbol"]
                token = instrument["instrument_token"]
                log(f'Scanning {instrument["trading_symbol"]} now')
                
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
                    
                    # Publish the eligible instrument immediately
                    self.add_tokens_to_subscribed_trade_sessions([instrument_data], trade_session_id)
                else:
                    log(f'{eligibility_obj["message"]}')
                    
            scan_end_time = current_ist()
            scan_duration = (scan_end_time - scan_start_time).total_seconds()
            
            # Publish scan cycle completed status
            self.event_publisher.publish_scanner_status(
                user_id=user_id,
                trade_session_id=trade_session_id,
                scanner_type="udts",
                status="running",
                details={
                    "scan_cycle": counter,
                    "instruments_scanned": instrument_counter,
                    "eligible_found": eligible_instrument_counter,
                    "scan_duration_seconds": scan_duration
                }
            )
            
            log(f"Scan cycle {counter} completed - Duration: {scan_duration}s, Found: {eligible_instrument_counter}/{instrument_counter}")
            
            # Use wait instead of sleep to be interruptible
            self._stop_event.wait(timeout=30)
        
        # Scanner stopped
        self._is_running = False
        self.event_publisher.publish_scanner_status(
            user_id=user_id,
            trade_session_id=trade_session_id,
            scanner_type="udts",
            status="stopped",
            details={"total_cycles": counter}
        )
        log(f"Scanner thread for {self.trade_frequency} stopped after {counter} cycles")

    def add_tokens_to_subscribed_trade_sessions(self, eligible_instruments, trade_session_id):
        """
        Publish eligible instruments to Redis stream for consumption by other services.
        
        Args:
            eligible_instruments: List of eligible instrument dictionaries in standardized format
            trade_session_id: Trade session ID for event correlation
        """
        self._ensure_configured()
        
        if not self.event_publisher:
            log("Event publisher not available, cannot publish eligible instruments", level="error")
            return
        
        for instrument in eligible_instruments:
            try:
                # Publish the eligible instrument event using standardized format
                message_id = self.event_publisher.publish_eligible_instrument(
                    trade_session_id=trade_session_id,
                    instrument_data=instrument,
                    scanner_type="udts"
                )
                
                if message_id:
                    log(f"Published eligible instrument: {instrument['trading_symbol']} - Message ID: {message_id}")
                else:
                    log(f"Failed to publish eligible instrument: {instrument['trading_symbol']}", level="warning")
                    
            except Exception as e:
                log(f"Error publishing eligible instrument {instrument.get('trading_symbol', 'unknown')}: {str(e)}", level="error")

    def __get_required_actions__(self, effective_trend):
        required_action = None
        if effective_trend == Trends.UPTREND:
            required_action = OrderType.BUY.value
        elif effective_trend == Trends.DOWNTREND:
            required_action = OrderType.SELL.value
        else:
            required_action = None
        return required_action

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

    def fetch_instrument_tokens_and_start_tracking(self, user_id, trade_session_id, dummy):
        self._ensure_configured()
        
        instrument_list = self.fetch_instruments()
        self.scan_instruments(instrument_list, user_id, trade_session_id, dummy)

    def scan_instruments(self, all_instruments, user_id, trade_session_id, dummy):
        self._ensure_configured()
        
        # Store the thread reference
        thread_name = f"scanner_thread_udts_{self.trade_frequency}"
        self._scanner_thread = threading.Thread(
            target=self.scan_in_separate_thread,
            args=(all_instruments, user_id, trade_session_id, dummy),
            name=thread_name
        )
        self._scanner_thread.daemon = True
        self._scanner_thread.start()
        log(f"Started scanner thread: {thread_name}")

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

    def is_eligible(self, symbol):
        self._ensure_configured()
        
        eligibility_obj = {"message": str(symbol) + " : Eligible"}
        
        # Fetch Quotes using data provider
        quote_response = self.data_provider.get_quotes(symbol, DEFAULT_EXCHANGE)
        quote = quote_response.get("data", {})
        
        key = DEFAULT_EXCHANGE+":"+symbol.upper()
        if key not in quote:
            eligibility_obj["message"] = symbol + " : No Data Fetched from quotes"
            return False, eligibility_obj
        token = quote[key]["instrument_token"]
        quote_data = quote[key]
        trade_freq =  self.trade_frequency
        frq_steps = FREQUENCY_STEPS[trade_freq]
        number_of_candles = NUM_CANDLES_FOR_TREND_ANALYSIS
        is_volume_eligible = self.get_volume_eligibility(quote_data)
        if (not is_volume_eligible):
            eligibility_obj["message"] = symbol + " : Volume not eligible"
            return False, eligibility_obj
        
        for index in range(0,len(frq_steps)):
            freq = frq_steps[index]
            eligibility_obj[freq] = {}
            # Use data provider instead of FetchData
            eligibility_obj[freq]["data"] = self.data_provider.fetch_historical_candle_data_from_kite(
                symbol, token, frq_steps[index], number_of_candles
            )
            if(len(eligibility_obj[freq]["data"]) < NUM_CANDLES_FOR_TREND_ANALYSIS): #For This frequency no data was fetched
                eligibility_obj["message"] = symbol + " : Not Enough Candles For " + str(freq)
                return False , eligibility_obj
            eligibility_obj[freq]["chart"] = CandleChart(symbol,token,quote_data["last_price"],quote_data["volume"],quote_data["last_quantity"],frq_steps[index],eligibility_obj[freq]["data"])
            eligibility_obj[freq]["chart"].set_trend_and_deflection_points()
        # USe Center element for scope
        deflection_points_scope =  self.__get_deflection_points_scope(eligibility_obj[frq_steps[SCOPE_COLLECTION_FREQ_INDEX]]["chart"])
        eligibility_obj[trade_freq]["chart"].normalise_deflection_points(deflection_points_scope)
        eligibility_obj[trade_freq]["chart"].set_trading_levels_and_ratios()
        effective_trend = self.__get_effective_trend(eligibility_obj)
        eligibility_obj["effective_trend"] = effective_trend

        if(not eligibility_obj[trade_freq]["chart"].valid_pairs or len(eligibility_obj[trade_freq]["chart"].valid_pairs)<1):
            eligibility_obj["message"] = symbol + " : No Valid Trading pairs Present"
            return False, eligibility_obj

        reward_risk_ratio = eligibility_obj[trade_freq]["chart"].trading_pair["reward_risk_ratio"] if "reward_risk_ratio" in eligibility_obj[trade_freq]["chart"].trading_pair else 0
        eligibility_obj["message"] = f"{symbol} : {effective_trend.value} , Reward:Risk - {reward_risk_ratio}"
        if(reward_risk_ratio > MINIMUM_REWARD_RISK_RATIO ):
            return True,eligibility_obj

        return False,eligibility_obj

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

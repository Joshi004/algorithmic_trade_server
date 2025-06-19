import os
import time
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from trade_management_unit.models import TradeSession, ScanningAlgorithm
from trade_management_unit.lib.common.event_publisher import TradeSessionEventPublisher
from scanning_service.lib.utils.redis.scanner_lock_manager import ScannerLockManager
from scanning_service.lib.utils.logger import log


class SessionProcessorMonitor:
    """
    Monitors session processors and triggers resume events for orphaned trade sessions.
    Currently supports scanners, with future extensibility for initiators and terminators.
    """
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.lock_manager = ScannerLockManager()
        self.event_publisher = TradeSessionEventPublisher()
        self.stats = {
            'orphaned_processors_found': 0,
            'resume_events_triggered': 0,
            'errors_encountered': 0,
            'total_active_sessions': 0
        }
        
    def monitor_scanners(self) -> Dict[str, int]:
        """
        Monitor scanner processors and trigger resume events for orphaned sessions.
        
        Returns:
            Dict with monitoring statistics
        """
        try:
            log("Starting scanner processor monitoring...")
            
            # Get all unique scanner+frequency combinations with active trade sessions
            scanner_combinations = self._get_active_scanner_combinations()
            
            if not scanner_combinations:
                log("No active trade sessions found requiring scanners")
                return self.stats
            
            log(f"Found {len(scanner_combinations)} unique scanner combinations to monitor")
            self.stats['total_active_sessions'] = sum(combo['session_count'] for combo in scanner_combinations)
            
            # Check each combination for missing locks
            for combo in scanner_combinations:
                try:
                    self._check_scanner_combination(combo)
                except Exception as e:
                    log(f"Error checking scanner combination {combo['algorithm_name']}:{combo['frequency']}: {str(e)}", level="error")
                    self.stats['errors_encountered'] += 1
            
            # Log summary
            self._log_monitoring_summary()
            return self.stats
            
        except Exception as e:
            log(f"Fatal error in scanner monitoring: {str(e)}", level="error")
            self.stats['errors_encountered'] += 1
            return self.stats
    
    def _get_active_scanner_combinations(self) -> List[Dict]:
        """
        Get all unique scanner algorithm + frequency combinations that have active trade sessions.
        
        Returns:
            List of dictionaries containing algorithm details and session counts
        """
        try:
            # Query active trade sessions grouped by scanner algorithm and frequency
            active_sessions = TradeSession.objects.filter(
                status='started',
                is_active=True
            ).select_related('scanning_algorithm').values(
                'scanning_algorithm_id',
                'scanning_algorithm__name',
                'trading_frequency'
            ).distinct()
            
            # Count sessions for each combination
            combinations = []
            for session_group in active_sessions:
                session_count = TradeSession.objects.filter(
                    scanning_algorithm_id=session_group['scanning_algorithm_id'],
                    trading_frequency=session_group['trading_frequency'],
                    status='started',
                    is_active=True
                ).count()
                
                combinations.append({
                    'algorithm_id': session_group['scanning_algorithm_id'],
                    'algorithm_name': session_group['scanning_algorithm__name'],
                    'frequency': session_group['trading_frequency'],  
                    'session_count': session_count
                })
            
            return combinations
            
        except Exception as e:
            log(f"Error getting active scanner combinations: {str(e)}", level="error")
            return []
    
    def _check_scanner_combination(self, combo: Dict):
        """
        Check if a scanner combination has a valid lock, trigger resume if not.
        
        Args:
            combo: Dictionary with algorithm_id, algorithm_name, frequency, session_count
        """
        algorithm_id = combo['algorithm_id']
        algorithm_name = combo['algorithm_name']
        frequency = combo['frequency']
        session_count = combo['session_count']
        
        # Check if lock exists for this combination
        lock_exists, lock_owner = self.lock_manager.check_lock(algorithm_id, frequency)
        
        if lock_exists:
            log(f"✅ Scanner {algorithm_name}:{frequency} has active lock (owner: {lock_owner}) - {session_count} sessions")
            return
        
        # No lock found - this is an orphaned processor combination
        log(f"🚨 ORPHANED: Scanner {algorithm_name}:{frequency} missing lock with {session_count} active sessions")
        self.stats['orphaned_processors_found'] += 1
        
        if self.dry_run:
            log(f"[DRY-RUN] Would trigger resume event for {algorithm_name}:{frequency}")
            return
        
        # Trigger resume event
        success = self._trigger_resume_event(algorithm_id, frequency, algorithm_name, session_count)
        if success:
            self.stats['resume_events_triggered'] += 1
            log(f"✅ Resume event triggered for {algorithm_name}:{frequency}")
        else:
            log(f"❌ Failed to trigger resume event for {algorithm_name}:{frequency}", level="error")
            self.stats['errors_encountered'] += 1
    
    def _trigger_resume_event(self, algorithm_id: int, frequency: str, algorithm_name: str, session_count: int) -> bool:
        """
        Trigger a resume scanner event for the given algorithm and frequency.
        
        Args:
            algorithm_id: Scanning algorithm ID
            frequency: Trading frequency
            algorithm_name: Algorithm name for logging
            session_count: Number of active sessions
            
        Returns:
            bool: True if event published successfully
        """
        try:
            # Get one active session to use as reference for the event
            reference_session = TradeSession.objects.filter(
                scanning_algorithm_id=algorithm_id,
                trading_frequency=frequency,
                status='started',
                is_active=True
            ).first()
            
            if not reference_session:
                log(f"No reference session found for {algorithm_name}:{frequency}", level="error")
                return False
            
            # Publish resume event using existing publisher
            success = self.event_publisher.publish_resume_scanner_event(reference_session)
            
            if success:
                log(f"Published resume scanner event for {algorithm_name}:{frequency} ({session_count} active sessions)")
            else:
                log(f"Failed to publish resume scanner event for {algorithm_name}:{frequency}", level="error")
                
            return success
            
        except Exception as e:
            log(f"Error triggering resume event for {algorithm_name}:{frequency}: {str(e)}", level="error")
            return False
    
    def _log_monitoring_summary(self):
        """Log a summary of the monitoring cycle."""
        log("=" * 60)
        log("SESSION PROCESSOR MONITORING SUMMARY")
        log("=" * 60)
        log(f"Total active trade sessions: {self.stats['total_active_sessions']}")
        log(f"Orphaned processors found: {self.stats['orphaned_processors_found']}")
        log(f"Resume events triggered: {self.stats['resume_events_triggered']}")
        log(f"Errors encountered: {self.stats['errors_encountered']}")
        if self.dry_run:
            log("🔍 DRY-RUN MODE: No actual resume events were triggered")
        log("=" * 60)


class Command(BaseCommand):
    """
    Django management command to monitor session processors and resume orphaned ones.
    
    Usage:
        # Single check
        python manage.py monitor_session_processors
        
        # Run as daemon
        python manage.py monitor_session_processors --daemon
        
        # Dry run mode
        python manage.py monitor_session_processors --dry-run
    """
    
    help = 'Monitor session processors (scanners, initiators, terminators) and resume orphaned ones'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.monitor = None
        self._running = False
        self._start_time = None
    
    def add_arguments(self, parser):
        """Add command line arguments"""
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run as daemon with periodic checks (default: single check)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without taking action',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=None,
            help='Interval in seconds between checks in daemon mode (default: from env MONITOR_INTERVAL_SECONDS or 300)',
        )
        parser.add_argument(
            '--processor-type',
            choices=['scanner', 'initiator', 'terminator', 'all'],
            default='scanner',
            help='Type of processor to monitor (default: scanner, others coming soon)',
        )
        parser.add_argument(
            '--health-check',
            action='store_true',
            help='Run health check and exit',
        )
    
    def handle(self, *args, **options):
        """Main command handler"""
        try:
            self._start_time = timezone.now()
            
            # Initialize monitor
            self.monitor = SessionProcessorMonitor(dry_run=options['dry_run'])
            
            # Set up signal handlers for graceful shutdown
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
            if options['health_check']:
                self._run_health_check()
            elif options['daemon']:
                self._run_daemon_mode(options)
            else:
                self._run_single_check(options)
                
        except KeyboardInterrupt:
            self.stdout.write("\nReceived interrupt signal, stopping gracefully...")
            log("Monitor interrupted by user")
        except Exception as e:
            log(f"Command failed: {str(e)}", level="error")
            raise CommandError(f"Failed to run session processor monitor: {str(e)}")
        finally:
            if self._start_time:
                duration = timezone.now() - self._start_time
                log(f"Monitor session completed. Total runtime: {duration}")
    
    def _run_health_check(self):
        """Run health check and exit"""
        self.stdout.write("Running health check for session processor monitor...")
        log("Running health check for session processor monitor...")
        
        try:
            # Check Redis connection
            if not self.monitor.lock_manager.redis_client.ping():
                raise Exception("Redis connection failed")
            
            # Check database connection
            with transaction.atomic():
                TradeSession.objects.first()
            
            # Check event publisher
            if not hasattr(self.monitor.event_publisher, 'redis_client'):
                raise Exception("Event publisher not properly initialized")
            
            self.stdout.write(self.style.SUCCESS("✅ Health check passed: All systems operational"))
            log("Health check passed: All systems operational")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Health check failed: {str(e)}"))
            log(f"Health check failed: {str(e)}", level="error")
            sys.exit(1)
    
    def _run_single_check(self, options):
        """Run a single monitoring check"""
        processor_type = options['processor_type']
        
        self.stdout.write(f"Running single {processor_type} processor check...")
        log(f"Running single {processor_type} processor check...")
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING("🔍 DRY-RUN MODE: No actual actions will be taken"))
        
        stats = self._run_monitoring_cycle(processor_type)
        self._display_results(stats)
    
    def _run_daemon_mode(self, options):
        """Run in daemon mode with periodic checks"""
        # Get interval from command line, environment, or default
        interval = options['interval']
        if interval is None:
            interval = int(os.environ.get('MONITOR_INTERVAL_SECONDS', 300))  # 5 minutes default
        
        processor_type = options['processor_type']
        
        self.stdout.write(f"Starting session processor monitor daemon...")
        self.stdout.write(f"Monitoring: {processor_type} processors")
        self.stdout.write(f"Check interval: {interval} seconds ({interval//60} minutes)")
        if options['dry_run']:
            self.stdout.write(self.style.WARNING("🔍 DRY-RUN MODE: No actual actions will be taken"))
        self.stdout.write("Press Ctrl+C to stop the daemon gracefully")
        
        log(f"Starting session processor monitor daemon - interval: {interval}s, type: {processor_type}")
        
        self._running = True
        cycle_count = 0
        
        try:
            while self._running:
                cycle_count += 1
                cycle_start = timezone.now()
                
                log(f"Starting monitoring cycle #{cycle_count}")
                stats = self._run_monitoring_cycle(processor_type)
                
                cycle_duration = timezone.now() - cycle_start
                log(f"Monitoring cycle #{cycle_count} completed in {cycle_duration.total_seconds():.2f}s")
                
                if not self._running:
                    break
                
                # Sleep with interrupt checking
                self._interruptible_sleep(interval)
                
        except Exception as e:
            log(f"Error in daemon mode: {str(e)}", level="error")
            raise
        finally:
            self._running = False
            log(f"Session processor monitor daemon stopped after {cycle_count} cycles")
    
    def _run_monitoring_cycle(self, processor_type: str) -> Dict[str, int]:
        """Run a single monitoring cycle for the specified processor type"""
        if processor_type in ['scanner', 'all']:
            return self.monitor.monitor_scanners()
        elif processor_type == 'initiator':
            # Future implementation
            log("Initiator monitoring not yet implemented", level="warning")
            return {}
        elif processor_type == 'terminator':
            # Future implementation  
            log("Terminator monitoring not yet implemented", level="warning")
            return {}
        else:
            raise ValueError(f"Unknown processor type: {processor_type}")
    
    def _display_results(self, stats: Dict[str, int]):
        """Display monitoring results to stdout"""
        if not stats:
            self.stdout.write("No statistics available")
            return
        
        self.stdout.write("\n" + "="*50)
        self.stdout.write("MONITORING RESULTS")
        self.stdout.write("="*50)
        
        for key, value in stats.items():
            formatted_key = key.replace('_', ' ').title()
            if key == 'errors_encountered' and value > 0:
                self.stdout.write(self.style.ERROR(f"{formatted_key}: {value}"))
            elif key == 'orphaned_processors_found' and value > 0:
                self.stdout.write(self.style.WARNING(f"{formatted_key}: {value}"))
            else:
                self.stdout.write(f"{formatted_key}: {value}")
        
        self.stdout.write("="*50 + "\n")
    
    def _interruptible_sleep(self, seconds: int):
        """Sleep for specified seconds, but check for interruption every second"""
        for _ in range(seconds):
            if not self._running:
                break
            time.sleep(1)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        signal_name = signal.Signals(signum).name
        log(f"Received {signal_name} signal, initiating graceful shutdown...")
        self.stdout.write(f"\nReceived {signal_name} signal, stopping gracefully...")
        self._running = False 
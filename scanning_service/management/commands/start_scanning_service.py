import signal
import sys
from django.core.management.base import BaseCommand, CommandError
from scanning_service.consumers.scanning_queue_consumer import ScanningQueueConsumer
from scanning_service.lib.utils.logger import log


class Command(BaseCommand):
    """
    Django management command to start the scanning queue service.
    
    Usage:
        python manage.py start_scanning_service
        
    The service will run until interrupted with Ctrl+C or a SIGTERM signal.
    """
    
    help = 'Start the scanning queue service to process trade session scanning events'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.consumer = None
    
    def add_arguments(self, parser):
        """Add command line arguments"""
        parser.add_argument(
            '--health-check',
            action='store_true',
            help='Run a health check instead of starting the service',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose logging',
        )
    
    def handle(self, *args, **options):
        """Main command handler"""
        try:
            # Initialize the consumer
            self.consumer = ScanningQueueConsumer()
            
            # Set up signal handlers for graceful shutdown
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
            if options['health_check']:
                self._run_health_check()
            else:
                self._start_service(options)
                
        except Exception as e:
            log(f"Command failed: {str(e)}", level="error")
            raise CommandError(f"Failed to start scanning service: {str(e)}")
    
    def _run_health_check(self):
        """Run a health check and exit"""
        self.stdout.write("Running health check for scanning service...")
        log("Running health check for scanning service...")
        
        if self.consumer.health_check():
            self.stdout.write(
                self.style.SUCCESS("Health check passed: Redis connection is working")
            )
            log("Health check passed: Redis connection is working")
        else:
            self.stdout.write(
                self.style.ERROR("Health check failed: Cannot connect to Redis")
            )
            log("Health check failed: Cannot connect to Redis", level="error")
            sys.exit(1)
    
    def _start_service(self, options):
        """Start the scanning service"""
        verbose = options.get('verbose', False)
        
        self.stdout.write("Starting scanning queue service...")
        self.stdout.write("Press Ctrl+C to stop the service gracefully")
        
        if verbose:
            log("Verbose logging enabled")
        
        log("Starting scanning queue service from management command")
        
        try:
            # Start consuming (this will block until interrupted)
            self.consumer.start_consuming()
        except KeyboardInterrupt:
            self.stdout.write("\nReceived interrupt signal, stopping service...")
            log("Received interrupt signal, stopping service...")
        except Exception as e:
            log(f"Service error: {str(e)}", level="error")
            raise
        finally:
            if self.consumer:
                self.consumer.stop_consuming()
            self.stdout.write("Scanning service stopped")
            log("Scanning service stopped")
    
    def _signal_handler(self, signum, frame):
        """Handle system signals for graceful shutdown"""
        signal_names = {
            signal.SIGINT: "SIGINT",
            signal.SIGTERM: "SIGTERM"
        }
        signal_name = signal_names.get(signum, f"Signal {signum}")
        
        self.stdout.write(f"\nReceived {signal_name}, stopping service gracefully...")
        log(f"Received {signal_name}, stopping service gracefully...")
        
        if self.consumer:
            self.consumer.stop_consuming()
        
        sys.exit(0) 
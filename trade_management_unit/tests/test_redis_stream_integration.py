"""
Test Redis Stream Integration for Trade Session Events

This test verifies that trade session initiation events are properly published to Redis streams.
Run this test to ensure Phase 1 implementation is working correctly.
"""
import os
import sys
import django
from unittest.mock import patch, MagicMock

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ats_base.settings')
django.setup()

from trade_management_unit.lib.common.Utils.redis_stream_client import get_redis_stream_client
from trade_management_unit.lib.common.event_publisher import get_trade_session_event_publisher
from trade_management_unit.models.TradeSession import TradeSession
from ats_gateway.models.User import User
from trade_management_unit.models.ScanningAlgorithm import ScanningAlgorithm
from trade_management_unit.models.InitiationAlgorithm import InitiationAlgorithm
from trade_management_unit.models.TerminationAlgorithm import TerminationAlgorithm


class TestRedisStreamIntegration:
    """Test Redis stream integration for trade session events"""
    
    def __init__(self):
        self.redis_client = get_redis_stream_client()
        self.event_publisher = get_trade_session_event_publisher()
    
    def test_redis_connection(self):
        """Test basic Redis connection"""
        print("\n=== Testing Redis Connection ===")
        
        try:
            is_healthy = self.redis_client.health_check()
            if is_healthy:
                print("✅ Redis connection successful")
                return True
            else:
                print("❌ Redis connection failed")
                return False
        except Exception as e:
            print(f"❌ Redis connection error: {str(e)}")
            return False
    
    def test_stream_publishing(self):
        """Test publishing a basic event to Redis stream"""
        print("\n=== Testing Stream Publishing ===")
        
        try:
            test_event = {
                "event_id": "test-12345",
                "event_type": "test_event",
                "timestamp": "2024-01-01T10:00:00+05:30",
                "test_data": "hello_world"
            }
            
            success = self.redis_client.publish_to_stream("test_queue", test_event)
            if success:
                print("✅ Stream publishing successful")
                return True
            else:
                print("❌ Stream publishing failed")
                return False
                
        except Exception as e:
            print(f"❌ Stream publishing error: {str(e)}")
            return False
    
    def test_event_publisher_health(self):
        """Test event publisher health check"""
        print("\n=== Testing Event Publisher Health ===")
        
        try:
            is_healthy = self.event_publisher.health_check()
            if is_healthy:
                print("✅ Event publisher health check successful")
                return True
            else:
                print("❌ Event publisher health check failed")
                return False
        except Exception as e:
            print(f"❌ Event publisher health check error: {str(e)}")
            return False
    
    def test_mock_trade_session_event(self):
        """Test event formatting with mock trade session data"""
        print("\n=== Testing Mock Trade Session Event ===")
        
        try:
            # Create mock objects
            mock_user = MagicMock()
            mock_user.public_id = "test-user-uuid-12345"
            
            mock_scanning_algo = MagicMock()
            mock_scanning_algo.id = 1
            
            mock_initiation_algo = MagicMock()
            mock_initiation_algo.id = 2
            
            mock_termination_algo = MagicMock()
            mock_termination_algo.id = 3
            
            mock_trade_session = MagicMock()
            mock_trade_session.id = 999
            mock_trade_session.user_id = mock_user
            mock_trade_session.scanning_algorithm = mock_scanning_algo
            mock_trade_session.initiation_algorithm = mock_initiation_algo
            mock_trade_session.termination_algorithm = mock_termination_algo
            mock_trade_session.trading_frequency = "5minute"
            mock_trade_session.dummy = True
            mock_trade_session.status = "started"
            mock_trade_session.started_at = None
            
            # Test event formatting
            event_data = self.event_publisher._format_trade_session_event(mock_trade_session)
            
            required_fields = [
                "event_id", "event_type", "timestamp", "trade_session_id",
                "user_id", "algorithm_config", "trading_frequency", "is_dummy", "session_status"
            ]
            
            missing_fields = [field for field in required_fields if field not in event_data]
            
            if not missing_fields:
                print("✅ Event formatting successful")
                print(f"   Event ID: {event_data['event_id']}")
                print(f"   Event Type: {event_data['event_type']}")
                print(f"   Trade Session ID: {event_data['trade_session_id']}")
                print(f"   User ID: {event_data['user_id']}")
                return True
            else:
                print(f"❌ Event formatting failed - missing fields: {missing_fields}")
                return False
                
        except Exception as e:
            print(f"❌ Event formatting error: {str(e)}")
            return False
    
    def test_integration_with_mock_publishing(self):
        """Test full integration with mock Redis publishing"""
        print("\n=== Testing Integration with Mock Publishing ===")
        
        try:
            # Mock the Redis client to avoid actual Redis calls
            with patch.object(self.redis_client, 'publish_to_stream', return_value=True) as mock_publish:
                # Create mock trade session
                mock_user = MagicMock()
                mock_user.public_id = "test-user-uuid-12345"
                
                mock_scanning_algo = MagicMock()
                mock_scanning_algo.id = 1
                
                mock_initiation_algo = MagicMock()
                mock_initiation_algo.id = 2
                
                mock_termination_algo = MagicMock()
                mock_termination_algo.id = 3
                
                mock_trade_session = MagicMock()
                mock_trade_session.id = 999
                mock_trade_session.user_id = mock_user
                mock_trade_session.scanning_algorithm = mock_scanning_algo
                mock_trade_session.initiation_algorithm = mock_initiation_algo
                mock_trade_session.termination_algorithm = mock_termination_algo
                mock_trade_session.trading_frequency = "5minute"
                mock_trade_session.dummy = True
                mock_trade_session.status = "started"
                mock_trade_session.started_at = None
                
                # Test event publishing
                success = self.event_publisher.publish_trade_session_initiated(
                    mock_trade_session, 
                    "New session created"
                )
                
                if success and mock_publish.called:
                    call_args = mock_publish.call_args
                    stream_name = call_args[0][0]
                    event_data = call_args[0][1]
                    
                    print("✅ Integration test successful")
                    print(f"   Stream Name: {stream_name}")
                    print(f"   Event Type: {event_data['event_type']}")
                    print(f"   Mock Redis publish called: {mock_publish.called}")
                    return True
                else:
                    print("❌ Integration test failed")
                    return False
                    
        except Exception as e:
            print(f"❌ Integration test error: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all tests and provide summary"""
        print("🚀 Starting Redis Stream Integration Tests...")
        print("=" * 60)
        
        test_results = []
        
        # Run individual tests
        test_results.append(("Redis Connection", self.test_redis_connection()))
        test_results.append(("Stream Publishing", self.test_stream_publishing()))
        test_results.append(("Event Publisher Health", self.test_event_publisher_health()))
        test_results.append(("Mock Event Formatting", self.test_mock_trade_session_event()))
        test_results.append(("Integration with Mock", self.test_integration_with_mock_publishing()))
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = 0
        failed = 0
        
        for test_name, result in test_results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{test_name:.<30} {status}")
            if result:
                passed += 1
            else:
                failed += 1
        
        print("-" * 60)
        print(f"Total Tests: {len(test_results)} | Passed: {passed} | Failed: {failed}")
        
        if failed == 0:
            print("\n🎉 All tests passed! Phase 1 implementation is working correctly.")
        else:
            print(f"\n⚠️  {failed} test(s) failed. Please check the Redis configuration and setup.")
        
        return failed == 0


def main():
    """Main function to run the tests"""
    tester = TestRedisStreamIntegration()
    return tester.run_all_tests()


if __name__ == "__main__":
    main()

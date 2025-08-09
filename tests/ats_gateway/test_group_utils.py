"""
Tests for ats_gateway.utils.group_utils

Section 1: get_group_name
- Standard naming convention
- Frequency passthrough without normalization
- Non-string algorithm_id handling (UUID, None)

Section 2: increment_group_subscription
- First increment behavior and TTL
- Consecutive increments and TTL refresh
- Isolation across different groups
"""

import uuid
import pytest
import time

from ats_gateway.utils.group_utils import (
    get_group_name,
    increment_group_subscription,
    decrement_group_subscription,
    get_group_subscription_count,
    cleanup_group_subscription,
)


@pytest.mark.unit
class TestGetGroupName:
    def test_standard_inputs_produce_expected_format(self):
        # Arrange
        algorithm_id = 2
        frequency = '10-minute'

        # Act
        result = get_group_name(algorithm_id, frequency)

        # Assert
        assert result == 'scanner_2_10-minute'

    def test_frequency_passthrough_without_normalization(self):
        # Arrange
        algorithm_id = 5
        frequency = '5Min'  # mixed case, should be returned as-is

        # Act
        result = get_group_name(algorithm_id, frequency)

        # Assert
        assert result == 'scanner_5_5Min'

    @pytest.mark.parametrize(
        "algorithm_id,frequency,expected_prefix,expected_suffix_check",
        [
            (uuid.uuid4(), 'daily', 'scanner_', lambda aid: f"{aid}"),
            (None, 'daily', 'scanner_', lambda aid: 'None'),
        ],
    )
    def test_non_string_algorithm_id_is_stringified(self, algorithm_id, frequency, expected_prefix, expected_suffix_check):
        # Act
        result = get_group_name(algorithm_id, frequency)

        # Assert
        # Must start with prefix and include the exact stringified algorithm_id
        assert result.startswith(expected_prefix)
        expected_id_str = expected_suffix_check(algorithm_id)
        assert result == f"scanner_{expected_id_str}_{frequency}"


@pytest.mark.integration
@pytest.mark.redis
class TestIncrementGroupSubscription:
    def test_first_increment_sets_count_1_and_ttl(self, redis_data_manager):
        # Arrange: unique group and ensure key absent
        group_name = f"scanner_test_{uuid.uuid4().hex}"
        redis_key = f"subs:{group_name}"
        redis_data_manager.redis_client.delete(redis_key)

        # Act
        count = increment_group_subscription(group_name)

        # Assert
        assert count == 1
        value = redis_data_manager.redis_client.get(redis_key)
        assert value == '1'
        ttl = redis_data_manager.redis_client.ttl(redis_key)
        # TTL should be set to ~3600 seconds
        assert 1 <= ttl <= 3600

        # Cleanup
        redis_data_manager.redis_client.delete(redis_key)

    def test_consecutive_increments_increase_count_and_refresh_ttl(self, redis_data_manager):
        # Arrange
        group_name = f"scanner_test_{uuid.uuid4().hex}"
        redis_key = f"subs:{group_name}"
        redis_data_manager.redis_client.delete(redis_key)

        # Act: first increment
        c1 = increment_group_subscription(group_name)
        ttl1 = redis_data_manager.redis_client.ttl(redis_key)
        time.sleep(0.2)
        # Second increment should raise count and refresh TTL
        c2 = increment_group_subscription(group_name)
        ttl2 = redis_data_manager.redis_client.ttl(redis_key)

        # Assert
        assert c1 == 1
        assert c2 == 2
        assert 1 <= ttl1 <= 3600
        assert 1 <= ttl2 <= 3600
        # TTL should be refreshed (reset closer to 3600), so ttl2 >= ttl1 is a reasonable check
        assert ttl2 >= ttl1

        # Cleanup
        redis_data_manager.redis_client.delete(redis_key)

    def test_isolation_between_different_groups(self, redis_data_manager):
        # Arrange
        group_a = f"scanner_test_{uuid.uuid4().hex}"
        group_b = f"scanner_test_{uuid.uuid4().hex}"
        key_a = f"subs:{group_a}"
        key_b = f"subs:{group_b}"
        redis_data_manager.redis_client.delete(key_a)
        redis_data_manager.redis_client.delete(key_b)
        # Act
        ca1 = increment_group_subscription(group_a)
        cb1 = increment_group_subscription(group_b)
        # Assert
        assert ca1 == 1
        assert cb1 == 1
        assert redis_data_manager.redis_client.get(key_a) == '1'
        assert redis_data_manager.redis_client.get(key_b) == '1'
        ttl_a = redis_data_manager.redis_client.ttl(key_a)
        ttl_b = redis_data_manager.redis_client.ttl(key_b)
        assert 1 <= ttl_a <= 3600
        assert 1 <= ttl_b <= 3600
        # Cleanup
        redis_data_manager.redis_client.delete(key_a)
        redis_data_manager.redis_client.delete(key_b)

@pytest.mark.integration
@pytest.mark.redis
class TestGetGroupSubscriptionCount:
    def test_returns_integer_count_for_existing_key(self, redis_data_manager):
        # Arrange
        group_name = f"scanner_test_{uuid.uuid4().hex}"
        key = f"subs:{group_name}"
        rc = redis_data_manager.redis_client
        rc.delete(key)

        # Make count = 2
        increment_group_subscription(group_name)
        increment_group_subscription(group_name)

        # Act
        count = get_group_subscription_count(group_name)

        # Assert
        assert count == 2
        assert rc.get(key) == '2'

        # Cleanup
        rc.delete(key)

    def test_returns_zero_for_missing_key(self, redis_data_manager):
        # Arrange
        group_name = f"scanner_test_{uuid.uuid4().hex}"
        key = f"subs:{group_name}"
        rc = redis_data_manager.redis_client
        rc.delete(key)

        # Act
        count = get_group_subscription_count(group_name)

        # Assert
        assert count == 0

@pytest.mark.integration
@pytest.mark.redis
class TestDecrementGroupSubscription:
    def test_decrement_from_two_to_one(self, redis_data_manager):
        # Arrange
        group_name = f"scanner_test_{uuid.uuid4().hex}"
        key = f"subs:{group_name}"
        rc = redis_data_manager.redis_client
        rc.delete(key)
        # Reach count=2
        increment_group_subscription(group_name)
        increment_group_subscription(group_name)

        # Act
        new_count = decrement_group_subscription(group_name)

        # Assert
        assert new_count == 1
        assert rc.get(key) == '1'

        # Cleanup
        rc.delete(key)

    def test_decrement_from_one_to_zero(self, redis_data_manager):
        # Arrange
        group_name = f"scanner_test_{uuid.uuid4().hex}"
        key = f"subs:{group_name}"
        rc = redis_data_manager.redis_client
        rc.delete(key)
        # Reach count=1
        increment_group_subscription(group_name)

        # Act
        new_count = decrement_group_subscription(group_name)

        # Assert
        assert new_count == 0
        assert rc.get(key) == '0'

        # Cleanup
        rc.delete(key)

    def test_decrement_from_missing_key_floors_to_zero(self, redis_data_manager):
        # Arrange
        group_name = f"scanner_test_{uuid.uuid4().hex}"
        key = f"subs:{group_name}"
        rc = redis_data_manager.redis_client
        rc.delete(key)

        # Act
        new_count = decrement_group_subscription(group_name)

        # Assert
        assert new_count == 0
        assert rc.get(key) == '0'

        # Cleanup
        rc.delete(key)

        
@pytest.mark.integration
@pytest.mark.redis
class TestCleanupGroupSubscription:
    def test_cleanup_deletes_key_when_count_zero(self, redis_data_manager):
        # Arrange: make count zero
        group_name = f"scanner_test_{uuid.uuid4().hex}"
        key = f"subs:{group_name}"
        rc = redis_data_manager.redis_client
        rc.delete(key)
        increment_group_subscription(group_name)
        assert decrement_group_subscription(group_name) == 0
        assert rc.get(key) == '0'

        # Act: cleanup
        cleanup_group_subscription(group_name)

        # Assert: key removed
        assert rc.get(key) is None

    def test_cleanup_does_not_delete_when_count_positive(self, redis_data_manager):
        # Arrange: make count positive (2)
        group_name = f"scanner_test_{uuid.uuid4().hex}"
        key = f"subs:{group_name}"
        rc = redis_data_manager.redis_client
        rc.delete(key)
        increment_group_subscription(group_name)
        increment_group_subscription(group_name)
        assert rc.get(key) == '2'

        # Act: cleanup
        cleanup_group_subscription(group_name)

        # Assert: key still present with same value
        assert rc.get(key) == '2'



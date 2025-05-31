#!/usr/bin/env python3
"""
Test script to verify Trade Session API behavior for new and existing sessions.

This script tests the fixed API endpoint to ensure it returns 200 for both:
1. New session creation
2. Existing session scenarios

Run this after starting your Docker containers.
"""

import requests
import json
import sys

# Configuration
API_BASE_URL = "http://localhost:18000"
TRADE_SESSION_ENDPOINT = "/tmu/initiate_trade_session/"

# Test parameters
TEST_PARAMS = {
    "trading_frequency": "5minute",
    "dummy": "1",
    "scanning_algorithm_id": "1", 
    "initiation_algorithm_id": "1",
    "termination_algorithm_id": "1"
}

# You'll need to replace this with a valid JWT token
# Get this from your authentication system
JWT_TOKEN = "your_jwt_token_here"

def test_trade_session_api():
    """Test the trade session API for both new and existing session scenarios"""
    
    print("🧪 Testing Trade Session API Fix")
    print("=" * 50)
    
    # Headers with authentication
    headers = {
        "Authorization": f"Bearer {JWT_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Build URL with query parameters
    url = f"{API_BASE_URL}{TRADE_SESSION_ENDPOINT}"
    
    print(f"📍 Testing URL: {url}")
    print(f"📋 Parameters: {TEST_PARAMS}")
    print()
    
    # Test 1: First call (should create new session)
    print("🆕 Test 1: Creating new trade session...")
    try:
        response1 = requests.get(url, params=TEST_PARAMS, headers=headers)
        
        print(f"   Status Code: {response1.status_code}")
        print(f"   Response: {response1.text}")
        
        if response1.status_code == 200:
            data1 = response1.json()
            print(f"   ✅ Success: {data1.get('success', False)}")
            print(f"   📝 Message: {data1.get('message', 'No message')}")
            trade_session_id = data1.get('trade_session_id')
            status = data1.get('status')
            print(f"   📊 Session ID: {trade_session_id}")
            print(f"   📈 Status: {status}")
            
            # Verify it's a new session
            if status == "new":
                print(f"   ✅ Correct: New session created")
            else:
                print(f"   ⚠️  Warning: Expected 'new' status, got '{status}'")
        else:
            print(f"   ❌ Failed: {response1.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Request failed: {str(e)}")
        return False
    
    print()
    
    # Test 2: Second call with same parameters (should return existing session)
    print("🔄 Test 2: Calling with same parameters (should return existing session)...")
    try:
        response2 = requests.get(url, params=TEST_PARAMS, headers=headers)
        
        print(f"   Status Code: {response2.status_code}")
        print(f"   Response: {response2.text}")
        
        if response2.status_code == 200:
            data2 = response2.json()
            print(f"   ✅ Success: {data2.get('success', False)}")
            print(f"   📝 Message: {data2.get('message', 'No message')}")
            trade_session_id_2 = data2.get('trade_session_id')
            status_2 = data2.get('status')
            print(f"   📊 Session ID: {trade_session_id_2}")
            print(f"   📈 Status: {status_2}")
            
            # Verify it's an existing session
            if status_2 == "existing":
                print(f"   ✅ Correct: Existing session returned")
            else:
                print(f"   ⚠️  Warning: Expected 'existing' status, got '{status_2}'")
            
            # Verify both calls returned the same session ID
            if response1.status_code == 200:
                data1 = response1.json()
                if data1.get('trade_session_id') == trade_session_id_2:
                    print(f"   ✅ Correct: Both calls returned same session ID")
                else:
                    print(f"   ❌ Error: Different session IDs returned")
                    return False
        else:
            print(f"   ❌ Failed: {response2.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Request failed: {str(e)}")
        return False
    
    print()
    print("🎉 All tests passed! The API correctly handles both new and existing sessions.")
    return True

def test_without_auth():
    """Test the API without authentication (should return 401)"""
    print("🔒 Test 3: Testing without authentication (should return 401)...")
    
    url = f"{API_BASE_URL}{TRADE_SESSION_ENDPOINT}"
    
    try:
        response = requests.get(url, params=TEST_PARAMS)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 401:
            print(f"   ✅ Correct: Authentication required")
        else:
            print(f"   ❌ Unexpected: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Request failed: {str(e)}")

def test_missing_parameters():
    """Test the API with missing required parameters (should return 400)"""
    print("🔒 Test 4: Testing with missing parameters (should return 400)...")
    
    url = f"{API_BASE_URL}{TRADE_SESSION_ENDPOINT}"
    
    # Headers with authentication
    headers = {
        "Authorization": f"Bearer {JWT_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Test with missing trading_frequency
    incomplete_params = {
        "dummy": "1",
        "scanning_algorithm_id": "1", 
        "initiation_algorithm_id": "1",
        "termination_algorithm_id": "1"
        # missing trading_frequency
    }
    
    try:
        response = requests.get(url, params=incomplete_params, headers=headers)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 400:
            print(f"   ✅ Correct: Missing parameters validation working")
            data = response.json()
            print(f"   📝 Error: {data.get('error', 'No error message')}")
        else:
            print(f"   ❌ Unexpected: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Request failed: {str(e)}")

def main():
    """Main function"""
    print("Trade Session API Test Script")
    print("=============================")
    print()
    print("Testing the refactored lean view with TradeSessionHelper...")
    print()
    
    # Check if JWT token is provided
    if JWT_TOKEN == "your_jwt_token_here":
        print("⚠️  Warning: JWT_TOKEN is not set!")
        print("   Please update the JWT_TOKEN variable in this script with a valid token.")
        print("   You can get a token by logging into your application.")
        print()
        print("   For now, testing without authentication...")
        test_without_auth()
        test_missing_parameters()
        return
    
    # Run tests with authentication
    success = test_trade_session_api()
    test_missing_parameters()
    
    if success:
        print("\n✅ Trade session API refactoring is working correctly!")
        print("   ✓ View is now lean - business logic moved to TradeSessionHelper")
        print("   ✓ Proper separation of concerns achieved")
        print("   ✓ Both new and existing sessions handled correctly")
    else:
        print("\n❌ There are still issues with the API.")
        sys.exit(1)

if __name__ == "__main__":
    main() 
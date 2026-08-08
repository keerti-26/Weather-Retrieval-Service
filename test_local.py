#!/usr/bin/env python3
"""
Local test script for Weather Service App
Run this to verify the app works before deploying

Usage:
    python test_local.py
"""
import requests
import time
import sys

# Test configuration
BASE_URL = "http://localhost:8080"

def test_health():
    """Test the health endpoint"""
    print("\n🔍 Testing /health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health check passed!")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ Health check failed with status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to app: {e}")
        print("   Make sure the app is running: python app.py")
        return False

def test_home():
    """Test the home page"""
    print("\n🔍 Testing / (home page)...")
    try:
        response = requests.get(BASE_URL, timeout=5)
        if response.status_code == 200 and "Weather Retrieval Service" in response.text:
            print("✅ Home page loads successfully!")
            return True
        else:
            print(f"❌ Home page test failed with status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect: {e}")
        return False

def test_search():
    """Test the search endpoint"""
    print("\n🔍 Testing /weather/search endpoint...")
    
    test_query = {
        "query": "risk of flooding near rivers",
        "top_k": 5
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/weather/search",
            json=test_query,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if "results" in data:
                print("✅ Search endpoint works!")
                print(f"   Query: {data.get('query')}")
                print(f"   Results found: {len(data['results'])}")
                if len(data['results']) > 0:
                    print(f"   Sample result: {data['results'][0].get('location', 'N/A')}")
                else:
                    print("   ⚠️  No results (table might be empty)")
                return True
            else:
                print(f"❌ Unexpected response format: {data}")
                return False
        else:
            print(f"❌ Search failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Search request failed: {e}")
        return False

def main():
    print("="*60)
    print("🌦️  Weather Service Local Test Suite")
    print("="*60)
    
    print("\n⏳ Waiting for app to be ready (5 seconds)...")
    time.sleep(5)
    
    results = {
        "health": test_health(),
        "home": test_home(),
        "search": test_search()
    }
    
    print("\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 All tests passed! Your app is ready to deploy.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Fix the issues before deploying.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

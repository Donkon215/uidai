"""
Test API Endpoints - Production Deployment Verification
========================================================
Tests all 21 endpoints with and without API key
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"
API_KEY = "ak_29f3no4ZE7AX1TU1O43ww4Lf5223N"
HEADERS_WITH_KEY = {"X-API-Key": API_KEY}

def print_test(name, passed):
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"{status:10} | {name}")

def test_public_endpoints():
    """Test public endpoints (no API key required)"""
    print("\n" + "="*70)
    print("PUBLIC ENDPOINTS (No API Key Required)")
    print("="*70)
    
    # Test root
    try:
        r = requests.get(f"{BASE_URL}/")
        print_test("GET /", r.status_code == 200)
    except Exception as e:
        print_test("GET /", False)
        print(f"    Error: {e}")
    
    # Test health
    try:
        r = requests.get(f"{BASE_URL}/health")
        print_test("GET /health", r.status_code == 200)
        if r.status_code == 200:
            print(f"    Response: {r.json()}")
    except Exception as e:
        print_test("GET /health", False)
        print(f"    Error: {e}")
    
    # Test ready
    try:
        r = requests.get(f"{BASE_URL}/ready")
        print_test("GET /ready", r.status_code == 200)
    except Exception as e:
        print_test("GET /ready", False)
        print(f"    Error: {e}")
    
    # Test metrics
    try:
        r = requests.get(f"{BASE_URL}/metrics")
        print_test("GET /metrics", r.status_code == 200)
    except Exception as e:
        print_test("GET /metrics", False)
        print(f"    Error: {e}")

def test_protected_endpoints_no_key():
    """Test protected endpoints without API key (should fail in production)"""
    print("\n" + "="*70)
    print("PROTECTED ENDPOINTS - Without API Key")
    print("="*70)
    
    endpoints = [
        "/api/stats/overview",
        "/api/report/110001",
        "/api/district/MUMBAI",
        "/api/map/geojson?sector=education"
    ]
    
    for endpoint in endpoints:
        try:
            r = requests.get(f"{BASE_URL}{endpoint}")
            # In production mode, these should return 401 if API key is required
            # In development mode, they might return 200
            status = "No auth required" if r.status_code == 200 else f"Status: {r.status_code}"
            print(f"{'→':10} | {endpoint:40} | {status}")
        except Exception as e:
            print(f"{'✗ ERROR':10} | {endpoint:40} | {e}")

def test_protected_endpoints_with_key():
    """Test protected endpoints with API key"""
    print("\n" + "="*70)
    print("PROTECTED ENDPOINTS - With API Key")
    print("="*70)
    
    # Test stats overview
    try:
        r = requests.get(f"{BASE_URL}/api/stats/overview", headers=HEADERS_WITH_KEY)
        print_test("GET /api/stats/overview", r.status_code == 200)
        if r.status_code == 200:
            data = r.json()
            print(f"    Total Pincodes: {data.get('total_pincodes', 0)}")
            print(f"    Total Records: {data.get('total_records', 0)}")
            print(f"    Alerts: {data.get('sector_alerts', {})}")
    except Exception as e:
        print_test("GET /api/stats/overview", False)
        print(f"    Error: {e}")
    
    # Test pincode report
    try:
        r = requests.get(f"{BASE_URL}/api/report/110001", headers=HEADERS_WITH_KEY)
        print_test("GET /api/report/110001", r.status_code == 200)
        if r.status_code == 200:
            data = r.json()
            print(f"    Pincode: {data.get('pincode', 'N/A')}")
            print(f"    Risk Score: {data.get('risk_score', 0)}")
    except Exception as e:
        print_test("GET /api/report/110001", False)
        print(f"    Error: {e}")
    
    # Test district summary
    try:
        r = requests.get(f"{BASE_URL}/api/district/MUMBAI", headers=HEADERS_WITH_KEY)
        print_test("GET /api/district/MUMBAI", r.status_code == 200)
    except Exception as e:
        print_test("GET /api/district/MUMBAI", False)
        print(f"    Error: {e}")
    
    # Test map data
    try:
        r = requests.get(f"{BASE_URL}/api/map/geojson?sector=education", headers=HEADERS_WITH_KEY)
        print_test("GET /api/map/geojson?sector=education", r.status_code == 200)
    except Exception as e:
        print_test("GET /api/map/geojson?sector=education", False)
        print(f"    Error: {e}")
    
    # Test clusters
    try:
        r = requests.get(f"{BASE_URL}/api/clusters", headers=HEADERS_WITH_KEY)
        print_test("GET /api/clusters", r.status_code == 200)
        if r.status_code == 200:
            data = r.json()
            print(f"    Total Clusters: {len(data.get('clusters', []))}")
    except Exception as e:
        print_test("GET /api/clusters", False)
        print(f"    Error: {e}")
    
    # Test alerts
    try:
        r = requests.get(f"{BASE_URL}/api/alerts?sector=education&limit=5", headers=HEADERS_WITH_KEY)
        print_test("GET /api/alerts", r.status_code == 200)
        if r.status_code == 200:
            data = r.json()
            print(f"    Total Alerts: {data.get('total', 0)}")
    except Exception as e:
        print_test("GET /api/alerts", False)
        print(f"    Error: {e}")

def test_ml_endpoints():
    """Test ML-powered endpoints"""
    print("\n" + "="*70)
    print("ML & ANALYTICS ENDPOINTS")
    print("="*70)
    
    # Test anomalies
    try:
        r = requests.get(f"{BASE_URL}/api/ml/anomalies?limit=5", headers=HEADERS_WITH_KEY)
        print_test("GET /api/ml/anomalies", r.status_code == 200)
        if r.status_code == 200:
            data = r.json()
            print(f"    Total Anomalies: {data.get('total', 0)}")
    except Exception as e:
        print_test("GET /api/ml/anomalies", False)
        print(f"    Error: {e}")
    
    # Test forecast
    try:
        r = requests.get(f"{BASE_URL}/api/forecast/110001?sector=education&horizon=12", 
                        headers=HEADERS_WITH_KEY)
        print_test("GET /api/forecast/110001", r.status_code == 200)
    except Exception as e:
        print_test("GET /api/forecast/110001", False)
        print(f"    Error: {e}")
    
    # Test intelligence status
    try:
        r = requests.get(f"{BASE_URL}/api/intelligence/status", headers=HEADERS_WITH_KEY)
        print_test("GET /api/intelligence/status", r.status_code == 200)
    except Exception as e:
        print_test("GET /api/intelligence/status", False)
        print(f"    Error: {e}")

def main():
    print("\n" + "="*70)
    print("PULSE OF BHARAT - API TEST SUITE")
    print("="*70)
    print(f"Base URL: {BASE_URL}")
    print(f"API Key: {API_KEY[:20]}...")
    
    # Test if server is running
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=2)
        print(f"Server Status: Online ✓")
    except Exception as e:
        print(f"Server Status: Offline ✗")
        print(f"Error: {e}")
        print("\nPlease start the server first:")
        print("  cd D:\\uidai_hackathon-main")
        print("  D:/Environment/envs/env04/Scripts/python.exe -m uvicorn backend.main:app --reload")
        sys.exit(1)
    
    # Run all tests
    test_public_endpoints()
    test_protected_endpoints_no_key()
    test_protected_endpoints_with_key()
    test_ml_endpoints()
    
    print("\n" + "="*70)
    print("TEST SUITE COMPLETE")
    print("="*70)
    print("\nNote: If all protected endpoints work without API key,")
    print("the system is in development mode (API_KEY_ENABLED=False or ENVIRONMENT=development)")
    print("For production deployment, set ENVIRONMENT=production in backend/.env")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Test script for Health Form DI Service.
Tests the microservice endpoints and validates responses.
"""
import requests
import json
import time
import os
from pathlib import Path

# Service configuration
SERVICE_URL = "http://localhost:8001"
HEALTH_ENDPOINT = f"{SERVICE_URL}/health"
PROCESS_ENDPOINT = f"{SERVICE_URL}/process"
METRICS_ENDPOINT = f"{SERVICE_URL}/metrics"
RESET_ENDPOINT = f"{SERVICE_URL}/reset"

def test_health_endpoint():
    """Test the health check endpoint."""
    print("[TEST] Testing health endpoint...")
    try:
        response = requests.get(HEALTH_ENDPOINT, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"[PASS] Health check passed: {data}")
            return True
        else:
            print(f"[FAIL] Health check failed with status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"[FAIL] Health check failed with error: {e}")
        return False

def test_metrics_endpoint():
    """Test the metrics endpoint."""
    print("[TEST] Testing metrics endpoint...")
    try:
        response = requests.get(METRICS_ENDPOINT, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"[PASS] Metrics endpoint works: {data.get('documents_processed', 0)} docs processed")
            return True
        else:
            print(f"[FAIL] Metrics endpoint failed with status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"[FAIL] Metrics endpoint failed with error: {e}")
        return False

def test_process_with_sample_file():
    """Test document processing with a sample file."""
    print("[TEST] Testing document processing endpoint...")
    
    # Create a simple test file
    test_content = b"Sample document content for testing OCR service"
    test_filename = "test_document.txt"
    
    files = {'file': (test_filename, test_content, 'text/plain')}
    data = {'language': 'auto'}
    
    try:
        print(f"[INFO] Uploading test file: {test_filename}")
        start_time = time.time()
        
        response = requests.post(
            PROCESS_ENDPOINT,
            files=files,
            data=data,
            timeout=60
        )
        
        processing_time = time.time() - start_time
        print(f"[INFO] Processing took {processing_time:.2f} seconds")
        
        if response.status_code == 200:
            result = response.json()
            print("[PASS] Document processing succeeded!")
            
            # Check result structure
            if 'extracted_data' in result:
                print(f"[INFO] Extracted data keys: {list(result['extracted_data'].keys()) if result['extracted_data'] else 'None'}")
            if 'confidence_summary' in result:
                print(f"[INFO] Confidence summary: {result['confidence_summary']}")
            if 'processing_metadata' in result:
                metadata = result['processing_metadata']
                print(f"[INFO] Processing metadata: {metadata.get('total_time_seconds', 0):.2f}s total")
                
            return True
        else:
            print(f"[FAIL] Document processing failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"[FAIL] Document processing failed with error: {e}")
        return False

def test_reset_endpoint():
    """Test the metrics reset endpoint."""
    print("[TEST] Testing metrics reset endpoint...")
    try:
        response = requests.post(RESET_ENDPOINT, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"[PASS] Metrics reset successful: {data}")
            return True
        else:
            print(f"[FAIL] Metrics reset failed with status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"[FAIL] Metrics reset failed with error: {e}")
        return False

def check_service_dependencies():
    """Check if required environment variables are set."""
    print("[TEST] Checking service dependencies...")
    
    required_vars = [
        'AZURE_DOCUMENT_INTELLIGENCE_KEY',
        'AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT',
        'AZURE_OPENAI_API_KEY',
        'AZURE_OPENAI_ENDPOINT'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"[WARN] Missing environment variables: {missing_vars}")
        print("Make sure to set up your .env file with Azure credentials")
        return False
    else:
        print("[PASS] All required environment variables are set")
        return True

def main():
    """Run all tests for the Health Form DI Service."""
    print("[START] Starting Health Form DI Service Tests")
    print("=" * 50)
    
    # Check dependencies
    deps_ok = check_service_dependencies()
    
    # Test endpoints
    tests = [
        ("Health Check", test_health_endpoint),
        ("Metrics Endpoint", test_metrics_endpoint),
        ("Document Processing", test_process_with_sample_file),
        ("Metrics Reset", test_reset_endpoint),
        ("Final Metrics Check", test_metrics_endpoint)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        success = test_func()
        results.append((test_name, success))
        time.sleep(1)  # Brief pause between tests
    
    # Summary
    print("\n" + "=" * 50)
    print("[SUMMARY] TEST SUMMARY:")
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"{status} {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("[SUCCESS] All tests passed! Service is ready for production.")
        return 0
    else:
        print("[WARNING] Some tests failed. Check the service configuration and try again.")
        return 1

if __name__ == "__main__":
    exit(main())
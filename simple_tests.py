#!/usr/bin/env python3
"""
Simple Test Suite for GenAI OCR Chatbot (Windows Compatible)
"""
import requests
import time

SERVICE_URLS = {
    "phase1_ocr": "http://localhost:8001",
    "phase2_chat": "http://localhost:5000", 
    "metrics": "http://localhost:8031"
}

def test_service_health():
    """Test all service health endpoints"""
    print("\n*** TESTING SERVICE HEALTH ***")
    results = []
    
    for name, url in SERVICE_URLS.items():
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                print(f"  [PASS] {name}: Healthy")
                results.append(True)
            else:
                print(f"  [FAIL] {name}: HTTP {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"  [FAIL] {name}: {str(e)[:50]}...")
            results.append(False)
    
    return all(results)

def test_phase1_processing():
    """Test Phase 1 OCR processing"""
    print("\n*** TESTING PHASE 1 OCR ***")
    
    try:
        # Simple text file for testing
        test_content = "Sample text for testing".encode('utf-8')
        files = {'file': ('test.txt', test_content, 'text/plain')}
        data = {'language': 'auto'}
        
        response = requests.post(
            f"{SERVICE_URLS['phase1_ocr']}/process",
            files=files,
            data=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'extracted_data' in result:
                print("  [PASS] Phase 1: Processing successful")
                return True
            else:
                print("  [FAIL] Phase 1: Missing extracted_data")
                return False
        else:
            print(f"  [FAIL] Phase 1: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  [FAIL] Phase 1: {str(e)[:50]}...")
        return False

def test_phase2_chat():
    """Test Phase 2 Chat service"""
    print("\n*** TESTING PHASE 2 CHAT ***")
    
    try:
        payload = {
            "message": "What are dental benefits?",
            "language": "en",
            "user_profile": {},
            "conversation_history": []
        }
        
        response = requests.post(
            f"{SERVICE_URLS['phase2_chat']}/v1/chat",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'action' in result and 'intent' in result:
                print("  [PASS] Phase 2: Chat processing successful")
                return True
            else:
                print("  [FAIL] Phase 2: Missing action/intent")
                return False
        else:
            print(f"  [FAIL] Phase 2: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  [FAIL] Phase 2: {str(e)[:50]}...")
        return False

def test_metrics_service():
    """Test metrics service"""
    print("\n*** TESTING METRICS SERVICE ***")
    
    try:
        response = requests.get(f"{SERVICE_URLS['metrics']}/metrics", timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print("  [PASS] Metrics: Service responding")
            return True
        else:
            print(f"  [FAIL] Metrics: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  [FAIL] Metrics: {str(e)[:50]}...")
        return False

def main():
    """Run simple test suite"""
    print("*** GenAI OCR Chatbot - Simple Test Suite ***")
    print("=" * 60)
    
    tests = [
        ("Service Health", test_service_health),
        ("Phase 1 OCR", test_phase1_processing),
        ("Phase 2 Chat", test_phase2_chat),
        ("Metrics Service", test_metrics_service)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\nRunning: {test_name}")
        result = test_func()
        results.append((test_name, result))
        time.sleep(1)  # Brief pause between tests
    
    # Summary
    print("\n" + "=" * 60)
    print("*** TEST SUMMARY ***")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("*** SUCCESS: All tests passed! System ready for use. ***")
        return 0
    else:
        print("*** WARNING: Some tests failed. Check service status. ***")
        return 1

if __name__ == "__main__":
    exit(main())
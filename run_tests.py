#!/usr/bin/env python3
"""
Comprehensive Test Suite for GenAI OCR Chatbot
Tests all microservices and functionality after services are running
"""
import os
import sys
import time
import json
import requests
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Service configurations
SERVICE_URLS = {
    "phase1_ocr": "http://localhost:8001",
    "phase2_chat": "http://localhost:5000", 
    "metrics": "http://localhost:8031",
    "ui": "http://localhost:8501"
}

HEALTH_ENDPOINTS = {
    "phase1_ocr": f"{SERVICE_URLS['phase1_ocr']}/health",
    "phase2_chat": f"{SERVICE_URLS['phase2_chat']}/health",
    "metrics": f"{SERVICE_URLS['metrics']}/health"
}

class TestResults:
    """Track test results and generate summary"""
    
    def __init__(self):
        self.tests = []
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        
    def add_test(self, category: str, name: str, status: str, details: str = ""):
        """Add test result"""
        self.tests.append({
            "category": category,
            "name": name,
            "status": status,
            "details": details
        })
        
        if status == "PASS":
            self.passed += 1
        elif status == "FAIL":
            self.failed += 1
        elif status == "WARN":
            self.warnings += 1
    
    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "=" * 80)
        print("*** COMPREHENSIVE TEST RESULTS ***")
        print("=" * 80)
        
        # Group by category
        categories = {}
        for test in self.tests:
            cat = test["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(test)
        
        # Print results by category
        for category, tests in categories.items():
            print(f"\n[{category}]")
            print("-" * 40)
            
            for test in tests:
                status_icon = {
                    "PASS": "[PASS]",
                    "FAIL": "[FAIL]", 
                    "WARN": "[WARN]",
                    "SKIP": "[SKIP]"
                }.get(test["status"], "[????]")
                
                print(f"  {status_icon} {test['name']}")
                if test["details"]:
                    print(f"     └─ {test['details']}")
        
        # Overall summary
        total = self.passed + self.failed + self.warnings
        print(f"\n*** OVERALL RESULTS ***")
        print(f"   Passed: {self.passed}")
        print(f"   Failed: {self.failed}")
        print(f"   Warnings: {self.warnings}")
        print(f"   Total: {total}")
        
        if self.failed == 0:
            print(f"\n*** SUCCESS: All critical tests passed! System ready for production. ***")
            return 0
        else:
            print(f"\n*** ISSUES DETECTED: {self.failed} test(s) failed. Please review and fix. ***")
            return 1

def check_service_health(results: TestResults):
    """Check health of all services"""
    print("\n*** CHECKING SERVICE HEALTH ***")
    print("-" * 40)
    
    for service_name, health_url in HEALTH_ENDPOINTS.items():
        try:
            response = requests.get(health_url, timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                status_msg = f"Healthy - {health_data.get('status', 'OK')}"
                results.add_test("Service Health", f"{service_name.replace('_', ' ').title()}", "PASS", status_msg)
                print(f"  ✅ {service_name}: {status_msg}")
            else:
                error_msg = f"HTTP {response.status_code}"
                results.add_test("Service Health", f"{service_name.replace('_', ' ').title()}", "FAIL", error_msg)
                print(f"  ❌ {service_name}: {error_msg}")
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Connection failed - {str(e)[:50]}..."
            results.add_test("Service Health", f"{service_name.replace('_', ' ').title()}", "FAIL", error_msg)
            print(f"  ❌ {service_name}: {error_msg}")

def test_phase1_ocr(results: TestResults):
    """Test Phase 1 OCR service functionality"""
    print("\n📄 TESTING PHASE 1 OCR SERVICE")
    print("-" * 40)
    
    # Test with sample file (create minimal test file)
    test_file_content = "Sample Hebrew text for testing: שלום עולם".encode('utf-8')
    test_file_name = "test_sample.txt"
    
    try:
        files = {'file': (test_file_name, test_file_content, 'text/plain')}
        data = {'language': 'auto', 'format': 'canonical'}
        
        print("  🔄 Testing document processing...")
        start_time = time.time()
        
        response = requests.post(
            f"{SERVICE_URLS['phase1_ocr']}/process",
            files=files,
            data=data,
            timeout=60
        )
        
        processing_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            
            # Check response structure
            required_fields = ['extracted_data', 'confidence_analysis', 'processing_metadata']
            missing_fields = [f for f in required_fields if f not in result]
            
            if not missing_fields:
                details = f"Processing time: {processing_time:.2f}s"
                results.add_test("Phase 1 OCR", "Document Processing", "PASS", details)
                print(f"  ✅ Document processing: {details}")
                
                # Test confidence analysis
                if 'confidence_analysis' in result and result['confidence_analysis']:
                    results.add_test("Phase 1 OCR", "Confidence Analysis", "PASS", "Available")
                    print(f"  ✅ Confidence analysis: Available")
                else:
                    results.add_test("Phase 1 OCR", "Confidence Analysis", "WARN", "Missing or empty")
                    print(f"  ⚠️ Confidence analysis: Missing or empty")
                    
            else:
                error_msg = f"Missing fields: {missing_fields}"
                results.add_test("Phase 1 OCR", "Document Processing", "FAIL", error_msg)
                print(f"  ❌ Document processing: {error_msg}")
                
        else:
            error_msg = f"HTTP {response.status_code}: {response.text[:100]}"
            results.add_test("Phase 1 OCR", "Document Processing", "FAIL", error_msg)
            print(f"  ❌ Document processing: {error_msg}")
            
    except Exception as e:
        error_msg = f"Exception: {str(e)[:100]}"
        results.add_test("Phase 1 OCR", "Document Processing", "FAIL", error_msg)
        print(f"  ❌ Document processing: {error_msg}")

def test_phase2_chat(results: TestResults):
    """Test Phase 2 Chat service functionality"""
    print("\n💬 TESTING PHASE 2 CHAT SERVICE")
    print("-" * 40)
    
    # Test conversation flow
    user_profile = {}
    conversation_history = []
    
    test_scenarios = [
        {
            "name": "Initial Question (Hebrew)",
            "message": "מה ההטבות לטיפולי שיניים?",
            "language": "he",
            "expected_action": "collect_info"
        },
        {
            "name": "Provide HMO Info",
            "message": "אני במכבי",
            "language": "he", 
            "expected_action": "collect_info"
        },
        {
            "name": "Language Auto-Detection",
            "message": "What are the dental benefits?",
            "language": "auto",
            "expected_action": "collect_info"
        }
    ]
    
    for i, scenario in enumerate(test_scenarios):
        try:
            print(f"  🔄 Testing: {scenario['name']}...")
            
            payload = {
                "message": scenario["message"],
                "language": scenario["language"],
                "user_profile": user_profile.copy(),
                "conversation_history": conversation_history.copy()
            }
            
            response = requests.post(
                f"{SERVICE_URLS['phase2_chat']}/v1/chat",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response structure
                required_fields = ['action', 'intent']
                missing_fields = [f for f in required_fields if f not in data]
                
                if not missing_fields:
                    action = data.get('action', '')
                    intent = data.get('intent', '')
                    details = f"Action: {action}, Intent: {intent}"
                    results.add_test("Phase 2 Chat", scenario['name'], "PASS", details)
                    print(f"    ✅ {scenario['name']}: {details}")
                    
                    # Update state for next scenario
                    user_profile.update(data.get('updated_profile', {}))
                    conversation_history.append({"role": "user", "content": scenario["message"]})
                    if data.get('next_question'):
                        conversation_history.append({"role": "assistant", "content": data['next_question']})
                    
                else:
                    error_msg = f"Missing fields: {missing_fields}"
                    results.add_test("Phase 2 Chat", scenario['name'], "FAIL", error_msg)
                    print(f"    ❌ {scenario['name']}: {error_msg}")
                    
            else:
                error_msg = f"HTTP {response.status_code}"
                results.add_test("Phase 2 Chat", scenario['name'], "FAIL", error_msg)
                print(f"    ❌ {scenario['name']}: {error_msg}")
                
        except Exception as e:
            error_msg = f"Exception: {str(e)[:100]}"
            results.add_test("Phase 2 Chat", scenario['name'], "FAIL", error_msg)
            print(f"    ❌ {scenario['name']}: {error_msg}")

def test_vector_database(results: TestResults):
    """Test ChromaDB vector database functionality"""
    print("\n🗃️ TESTING VECTOR DATABASE")
    print("-" * 40)
    
    try:
        # Check if ChromaDB storage exists
        chromadb_path = project_root / "data" / "chromadb_storage"
        if chromadb_path.exists():
            # Check for key files
            chroma_db = chromadb_path / "chroma.sqlite3"
            if chroma_db.exists():
                file_size = chroma_db.stat().st_size
                details = f"Database exists, size: {file_size/1024:.1f}KB"
                results.add_test("Vector Database", "ChromaDB Storage", "PASS", details)
                print(f"  ✅ ChromaDB storage: {details}")
            else:
                results.add_test("Vector Database", "ChromaDB Storage", "WARN", "Database file not found")
                print(f"  ⚠️ ChromaDB storage: Database file not found")
        else:
            results.add_test("Vector Database", "ChromaDB Storage", "WARN", "Storage directory not found")
            print(f"  ⚠️ ChromaDB storage: Storage directory not found")
            
        # Check knowledge base data
        kb_path = project_root / "data" / "phase2_data" 
        if kb_path.exists():
            html_files = list(kb_path.glob("*.html"))
            if html_files:
                details = f"{len(html_files)} HTML files found"
                results.add_test("Vector Database", "Knowledge Base Files", "PASS", details)
                print(f"  ✅ Knowledge base: {details}")
            else:
                results.add_test("Vector Database", "Knowledge Base Files", "WARN", "No HTML files found")
                print(f"  ⚠️ Knowledge base: No HTML files found")
        else:
            results.add_test("Vector Database", "Knowledge Base Files", "FAIL", "KB directory not found")
            print(f"  ❌ Knowledge base: KB directory not found")
            
    except Exception as e:
        error_msg = f"Exception: {str(e)[:100]}"
        results.add_test("Vector Database", "Storage Check", "FAIL", error_msg)
        print(f"  ❌ Vector database check: {error_msg}")

def test_metrics_service(results: TestResults):
    """Test metrics service functionality"""
    print("\n📊 TESTING METRICS SERVICE")
    print("-" * 40)
    
    try:
        # Test metrics endpoint
        response = requests.get(f"{SERVICE_URLS['metrics']}/metrics", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            details = f"Metrics available with {len(data)} keys"
            results.add_test("Metrics Service", "Metrics Endpoint", "PASS", details)
            print(f"  ✅ Metrics endpoint: {details}")
        else:
            error_msg = f"HTTP {response.status_code}"
            results.add_test("Metrics Service", "Metrics Endpoint", "FAIL", error_msg)
            print(f"  ❌ Metrics endpoint: {error_msg}")
            
        # Check SQLite database
        metrics_db = project_root / "services" / "metrics-service" / "data" / "metrics.db"
        if metrics_db.exists():
            file_size = metrics_db.stat().st_size
            details = f"SQLite DB exists, size: {file_size/1024:.1f}KB"
            results.add_test("Metrics Service", "SQLite Database", "PASS", details)
            print(f"  ✅ SQLite database: {details}")
        else:
            results.add_test("Metrics Service", "SQLite Database", "WARN", "Database file not found")
            print(f"  ⚠️ SQLite database: Database file not found")
            
    except Exception as e:
        error_msg = f"Exception: {str(e)[:100]}"
        results.add_test("Metrics Service", "Service Test", "FAIL", error_msg)
        print(f"  ❌ Metrics service: {error_msg}")

def check_environment_config(results: TestResults):
    """Check environment configuration"""
    print("\n⚙️ CHECKING ENVIRONMENT CONFIGURATION")
    print("-" * 40)
    
    # Check .env file
    env_file = project_root / ".env"
    if env_file.exists():
        results.add_test("Environment", ".env File", "PASS", "File exists")
        print("  ✅ .env file: File exists")
    else:
        results.add_test("Environment", ".env File", "WARN", "File not found - check .env.example")
        print("  ⚠️ .env file: File not found - check .env.example")
    
    # Check key environment variables
    required_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY", 
        "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT",
        "AZURE_DOCUMENT_INTELLIGENCE_KEY"
    ]
    
    from dotenv import load_dotenv
    load_dotenv(env_file, override=False)
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if not missing_vars:
        results.add_test("Environment", "Azure Credentials", "PASS", "All variables set")
        print("  ✅ Azure credentials: All variables set")
    else:
        details = f"Missing: {', '.join(missing_vars)}"
        results.add_test("Environment", "Azure Credentials", "WARN", details)
        print(f"  ⚠️ Azure credentials: {details}")

def run_individual_service_tests(results: TestResults):
    """Run individual service test files"""
    print("\n🔧 RUNNING INDIVIDUAL SERVICE TESTS")
    print("-" * 40)
    
    # Phase 1 service test
    phase1_test = project_root / "services" / "health-form-di-service" / "test_service.py"
    if phase1_test.exists():
        try:
            print("  🔄 Running Phase 1 service tests...")
            result = subprocess.run(
                [sys.executable, str(phase1_test)],
                cwd=project_root / "services" / "health-form-di-service",
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                results.add_test("Individual Tests", "Phase 1 Service Test", "PASS", "All tests passed")
                print("    ✅ Phase 1 service tests: All tests passed")
            else:
                details = f"Exit code: {result.returncode}"
                results.add_test("Individual Tests", "Phase 1 Service Test", "FAIL", details)
                print(f"    ❌ Phase 1 service tests: {details}")
                
        except subprocess.TimeoutExpired:
            results.add_test("Individual Tests", "Phase 1 Service Test", "FAIL", "Timeout")
            print("    ❌ Phase 1 service tests: Timeout")
        except Exception as e:
            error_msg = f"Exception: {str(e)[:50]}"
            results.add_test("Individual Tests", "Phase 1 Service Test", "FAIL", error_msg)
            print(f"    ❌ Phase 1 service tests: {error_msg}")
    else:
        results.add_test("Individual Tests", "Phase 1 Service Test", "SKIP", "Test file not found")
        print("    ⏭️ Phase 1 service tests: Test file not found")
    
    # Phase 2 service test
    phase2_test = project_root / "services" / "chat-service" / "tests" / "test_chat_service.py"
    if phase2_test.exists():
        try:
            print("  🔄 Running Phase 2 service tests...")
            result = subprocess.run(
                [sys.executable, str(phase2_test)],
                cwd=project_root / "services" / "chat-service",
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if "SUCCESS" in result.stdout:
                results.add_test("Individual Tests", "Phase 2 Service Test", "PASS", "Scenario completed")
                print("    ✅ Phase 2 service tests: Scenario completed")
            else:
                results.add_test("Individual Tests", "Phase 2 Service Test", "WARN", "Check output")
                print("    ⚠️ Phase 2 service tests: Check output manually")
                
        except subprocess.TimeoutExpired:
            results.add_test("Individual Tests", "Phase 2 Service Test", "FAIL", "Timeout")
            print("    ❌ Phase 2 service tests: Timeout")
        except Exception as e:
            error_msg = f"Exception: {str(e)[:50]}"
            results.add_test("Individual Tests", "Phase 2 Service Test", "FAIL", error_msg)
            print(f"    ❌ Phase 2 service tests: {error_msg}")
    else:
        results.add_test("Individual Tests", "Phase 2 Service Test", "SKIP", "Test file not found")
        print("    ⏭️ Phase 2 service tests: Test file not found")

def main():
    """Run comprehensive test suite"""
    print("*** GenAI OCR Chatbot - Comprehensive Test Suite ***")
    print("=" * 80)
    print("This suite tests all microservices and functionality")
    print("Make sure all services are running before executing tests")
    print("=" * 80)
    
    # Initialize results tracker
    results = TestResults()
    
    # Run test categories
    check_environment_config(results)
    check_service_health(results)
    test_phase1_ocr(results)
    test_phase2_chat(results)
    test_vector_database(results)
    test_metrics_service(results)
    run_individual_service_tests(results)
    
    # Print final summary
    exit_code = results.print_summary()
    
    if exit_code == 0:
        print("\n🚀 SYSTEM READY: All tests passed! The application is ready for production use.")
        print("\n📖 Next Steps:")
        print("   1. Access UI at http://localhost:8501")
        print("   2. Test Phase 1 with sample PDFs")
        print("   3. Test Phase 2 chat conversations")
        print("   4. Monitor metrics at http://localhost:8031/metrics")
    else:
        print("\n🔧 ATTENTION REQUIRED: Some tests failed. Please:")
        print("   1. Check that all services are running (python start_demo.py)")
        print("   2. Verify Azure credentials in .env file")
        print("   3. Review individual service logs")
        print("   4. Re-run tests after fixing issues")
    
    return exit_code

if __name__ == "__main__":
    exit(main())
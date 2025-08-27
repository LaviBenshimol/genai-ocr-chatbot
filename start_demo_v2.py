#!/usr/bin/env python3
"""
Enhanced Demo Starter V2 - GenAI OCR Chatbot
Starts all services with the V2 enhanced chat service
"""
import subprocess
import time
import sys
import os
import requests
from pathlib import Path

def print_banner():
    print("=" * 50)
    print("GenAI OCR Chatbot - Enhanced Demo V2")
    print("=" * 50)

def check_service_health(url, service_name, timeout=30):
    """Check if service is healthy"""
    for _ in range(timeout):
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                return True
        except:
            pass
        time.sleep(1)
    print(f"[WARN] {service_name} health check failed")
    return False

def start_service(name, command, cwd=None):
    """Start a service in background"""
    print(f"{name}...")
    try:
        if cwd:
            process = subprocess.Popen(command, shell=True, cwd=cwd)
        else:
            process = subprocess.Popen(command, shell=True)
        return process
    except Exception as e:
        print(f"[FAIL] Failed to start {name}: {e}")
        return None

def main():
    print_banner()
    
    # Check if we're in the right directory
    if not os.path.exists("data/phase2_data") or not os.path.exists("services"):
        print("[FAIL] Please run this script from the project root directory")
        sys.exit(1)
    
    processes = []
    
    try:
        # 1. Start Enhanced Chat Service V2
        print("1. Starting Enhanced Chat Service V2...")
        chat_cmd = "python run.py"
        chat_process = start_service(
            "Enhanced Chat Service V2", 
            chat_cmd, 
            cwd="services/chat-service-v2"
        )
        if chat_process:
            processes.append(("Enhanced Chat Service V2", chat_process))
            print("  Waiting for enhanced chat service...")
            time.sleep(5)
            
            # Check for startup message
            if check_service_health("http://127.0.0.1:5002/health", "Enhanced Chat Service V2"):
                print("[OK] Enhanced Chat Service V2 ready")
                
                # Get service info
                try:
                    info_response = requests.get("http://127.0.0.1:5002/v2/info", timeout=5)
                    if info_response.status_code == 200:
                        info = info_response.json()
                        print(f"   Categories: {len(info.get('categories', []))}")
                        print(f"   Total services: {info.get('total_services', 0)}")
                        print(f"   Embeddings: {'OK' if info.get('embeddings_enabled') else 'FAIL'}")
                except:
                    pass
            else:
                print("[FAIL] Enhanced Chat Service V2 failed to start properly")
        
        # 2. Start Phase 1 OCR Service
        print("2. Starting Phase 1 OCR Service...")
        ocr_cmd = "python app.py"
        ocr_process = start_service(
            "Phase 1 OCR Service", 
            ocr_cmd, 
            cwd="services/health-form-di-service"
        )
        if ocr_process:
            processes.append(("Phase 1 OCR Service", ocr_process))
            time.sleep(3)
            if check_service_health("http://127.0.0.1:8001/health", "Phase 1 OCR Service"):
                print("[OK] Phase 1 OCR Service ready")
        
        # 3. Start Metrics Service
        print("3. Starting Metrics Service...")
        metrics_cmd = "python app.py"
        metrics_process = start_service(
            "Metrics Service", 
            metrics_cmd, 
            cwd="services/metrics-service"
        )
        if metrics_process:
            processes.append(("Metrics Service", metrics_process))
            time.sleep(2)
            if check_service_health("http://127.0.0.1:8031/health", "Metrics Service"):
                print("[OK] Metrics Service ready")
        
        # 4. Service Health Check Summary
        print("4. Service Health Check:")
        services_status = []
        
        if check_service_health("http://127.0.0.1:8001/health", "OCR Service", timeout=5):
            print("  [OK] OCR Service (Phase 1): HEALTHY")
            services_status.append("OCR")
        else:
            print("  [FAIL] OCR Service (Phase 1): UNHEALTHY")
            
        if check_service_health("http://127.0.0.1:5002/health", "Enhanced Chat Service V2", timeout=5):
            print("  [OK] Enhanced Chat Service V2 (Phase 2): HEALTHY")
            services_status.append("Chat V2")
        else:
            print("  [FAIL] Enhanced Chat Service V2 (Phase 2): UNHEALTHY")
            
        if check_service_health("http://127.0.0.1:8031/health", "Metrics Service", timeout=5):
            print("  [OK] Metrics Service: HEALTHY")
            services_status.append("Metrics")
        else:
            print("  [FAIL] Metrics Service: UNHEALTHY")
        
        print(f"Services Ready: {len(services_status)}/3")
        
        # 5. Start Streamlit UI
        print("5. Starting Streamlit UI...")
        print("Opening browser at: http://localhost:8501")
        
        # Instructions
        print("\\n[DEMO] Enhanced Demo V2 Instructions:")
        print("- Phase 1: PDF/image OCR field extraction (needs Azure DI credentials)")
        print("- Phase 2: Enhanced medical chatbot with improved retrieval")
        print("- Phase 3: Analytics dashboard with interactive visualizations")
        print("- V2 Features: Better fallback logic, polite collection, service scope detection")
        print("- Test queries: Hebrew dental questions or 'Eye exams benefits'")
        print("- V2 Chat API: http://localhost:5002/v2/chat")
        print("- Service Info API: http://localhost:5002/v2/info")
        print("- Analytics API: http://localhost:8031/dashboard/combined")
        
        # 5. Start Streamlit UI automatically
        print("\\n6. Starting Streamlit UI...")
        ui_cmd = "streamlit run streamlit_app.py --server.port 8501"
        ui_process = start_service(
            "Streamlit UI",
            ui_cmd,
            cwd="ui"
        )
        if ui_process:
            processes.append(("Streamlit UI", ui_process))
            time.sleep(3)
            print("[OK] Streamlit UI started at http://localhost:8501")
        
        print("\\n[INFO] All services are running!")
        print("[INFO] Open your browser to: http://localhost:8501")
        print("[INFO] Press Ctrl+C to stop all services")
        
        # Keep services running
        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            raise
        
    except KeyboardInterrupt:
        print("\\n[STOP] Shutting down services...")
        for name, process in processes:
            try:
                process.terminate()
                print(f"[OK] Stopped {name}")
            except:
                pass
        sys.exit(0)
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

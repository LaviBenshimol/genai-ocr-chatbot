#!/usr/bin/env python3
"""
Simple Demo Starter - GenAI OCR Chatbot
Starts working services and UI for demo
"""
import os
import subprocess
import sys
import time
import requests
from pathlib import Path

def check_health(url, name):
    """Quick health check"""
    try:
        r = requests.get(f"{url}/health", timeout=3)
        if r.status_code == 200:
            print(f"  {name}: HEALTHY")
            return True
    except:
        pass
    print(f"  {name}: OFFLINE")
    return False

def main():
    print("=" * 50)
    print("GenAI OCR Chatbot - Demo Starter")  
    print("=" * 50)
    
    project_root = Path(__file__).parent
    
    print("\n1. Starting Phase 2 Chat Service...")
    
    # Start the chat service we know works
    chat_script = project_root / "temp_chat_starter.py"
    
    # Create temporary chat starter script
    with open(chat_script, 'w') as f:
        f.write('''#!/usr/bin/env python3
import sys, os
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'services' / 'chat-service'))

# Disable embeddings for demo
import app.services.service_based_kb as kb_module
kb_module.AZURE_OPENAI_AVAILABLE = False

from app.main import create_app
app = create_app()
print(f'Chat service ready with {len(app.kb.service_chunks)} chunks')
app.run(host='127.0.0.1', port=5000, debug=False)
''')
    
    chat_proc = subprocess.Popen([
        sys.executable, str(chat_script)
    ], cwd=project_root)
    
    print("  Waiting for chat service...")
    time.sleep(5)
    
    print("\n2. Starting Phase 1 OCR Service...")
    # Start Phase 1 OCR service
    ocr_env = os.environ.copy()
    ocr_env["FLASK_APP"] = "app.py"
    ocr_env["FLASK_ENV"] = "development"
    
    ocr_proc = subprocess.Popen([
        sys.executable, "-m", "flask", "run",
        "--host", "127.0.0.1", "--port", "8001"
    ], cwd=project_root / "services" / "health-form-di-service", 
       env=ocr_env)
    
    time.sleep(3)  # Wait for OCR service
    
    print("\n3. Starting Metrics Service...")
    # Start metrics service
    metrics_proc = subprocess.Popen([
        sys.executable, "app.py"
    ], cwd=project_root / "services" / "metrics-service")
    
    time.sleep(2)  # Brief wait for metrics service
    
    print("\n4. Service Health Check:")
    ocr_healthy = check_health("http://127.0.0.1:8001", "OCR Service (Phase 1)")
    chat_healthy = check_health("http://127.0.0.1:5000", "Chat Service (Phase 2)")
    metrics_healthy = check_health("http://127.0.0.1:8031", "Metrics Service")
    
    required_services = int(ocr_healthy) + int(chat_healthy)
    print(f"\nServices Ready: {required_services}/2 required + {int(metrics_healthy)}/1 optional")
    
    if chat_healthy and ocr_healthy:
        print("\n5. Starting Streamlit UI...")
        print("Opening browser at: http://localhost:8501")
        print("\nDemo Instructions:")
        print("- Phase 1: PDF/image OCR field extraction (needs Azure DI credentials)")
        print("- Phase 2: Medical chatbot with persistent RAG")
        print("- Ask questions like: 'Eye exams Maccabi Gold' (Hebrew supported in UI)")
        print("\nPress Ctrl+C to stop")
        
        # Start Streamlit UI (blocking)
        ui_dir = project_root / "ui"
        try:
            subprocess.run([
                sys.executable, "-m", "streamlit", "run",
                "streamlit_app.py",
                "--server.port", "8501", 
                "--server.address", "127.0.0.1"
            ], cwd=ui_dir)
        finally:
            # Cleanup
            if chat_script.exists():
                chat_script.unlink()
            chat_proc.terminate()
            ocr_proc.terminate()
            metrics_proc.terminate()
    else:
        print("\nERROR: Chat service failed to start")
        print("Check Azure OpenAI credentials in config/settings.py")
        # Cleanup
        if chat_script.exists():
            chat_script.unlink()

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Main runner script for GenAI OCR Chatbot
Launches the Streamlit application with both Phase 1 and Phase 2 functionality
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def main():
    """Main entry point for the application"""
    print("🚀 Starting GenAI OCR Chatbot Application...")
    
    # Set the working directory to the script's directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Add src directory to Python path
    src_path = script_dir / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    
    print("📁 Project directory:", script_dir)
    print("🐍 Python path updated with src directory")
    
    # Launch Streamlit app
    streamlit_app_path = src_path / "ui" / "streamlit_app.py"
    
    if not streamlit_app_path.exists():
        print("❌ Streamlit app file not found. Creating basic structure...")
        create_basic_structure()
    
    print("🌐 Launching Streamlit application...")
    print("📍 Application will be available at: http://localhost:8501")
    print("⏹️  Press Ctrl+C to stop the application")
    
    try:
        # Install dependencies first
        print("📦 Installing/checking dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      capture_output=True, check=False)
        
        print("🚀 Starting Streamlit server...")
        
        # Create a process to run Streamlit with visible output
        process = subprocess.Popen([
            sys.executable, "-m", "streamlit", "run", 
            str(streamlit_app_path),
            "--server.port", "8501",
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false"
        ], text=True)  # Remove stdout/stderr capture to show output
        
        # Wait a moment for the server to start
        time.sleep(3)
        
        print("✅ Streamlit server started!")
        print("🌐 Access your application at:")
        print("   - http://localhost:8501")
        print("   - http://127.0.0.1:8501")
        print("\n⏹️  Press Ctrl+C to stop the application")
        
        # Wait for process to complete or be interrupted
        process.wait()
        
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
        if 'process' in locals():
            process.terminate()
    except Exception as e:
        print(f"❌ Error running application: {e}")
        sys.exit(1)

def create_basic_structure():
    """Create basic project structure if missing"""
    print("🔧 Creating basic project structure...")
    
    # Create __init__.py files
    init_files = [
        "src/__init__.py",
        "src/phase1/__init__.py", 
        "src/phase2/__init__.py",
        "src/shared/__init__.py",
        "src/ui/__init__.py",
        "config/__init__.py",
        "tests/__init__.py"
    ]
    
    for init_file in init_files:
        path = Path(init_file)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# Auto-generated __init__.py\n")
    
    print("✅ Basic structure created")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Debug launcher for GenAI OCR Chatbot
Runs Streamlit directly without subprocess - better for debugging
"""

import os
import sys
from pathlib import Path

def main():
    """Debug entry point - runs Streamlit directly"""
    print("🐛 DEBUG MODE - Starting GenAI OCR Chatbot...")
    
    # Set the working directory to the script's directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Add src directory to Python path
    src_path = script_dir / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    
    print(f"📁 Debug directory: {script_dir}")
    print(f"🐍 Python path updated with src directory")
    print(f"🔍 Debug output will appear in this terminal")
    
    # Import and run streamlit directly (no subprocess)
    try:
        import streamlit.web.cli as stcli
        streamlit_app_path = str(src_path / "ui" / "streamlit_app.py")
        
        print(f"🚀 Starting Streamlit directly from: {streamlit_app_path}")
        print(f"🌐 Application will be at: http://localhost:8501")
        print(f"🔍 All debug print() statements will show here!")
        print("-" * 60)
        
        # Set up streamlit arguments
        sys.argv = [
            "streamlit",
            "run",
            streamlit_app_path,
            "--server.port=8501",
            "--server.headless=true",
            "--browser.gatherUsageStats=false"
        ]
        
        # Run streamlit directly (not in subprocess)
        stcli.main()
        
    except KeyboardInterrupt:
        print("\n🛑 Debug session stopped by user")
    except Exception as e:
        print(f"❌ Debug error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
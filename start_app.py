"""
Simple startup script for GenAI OCR Chatbot
Direct Streamlit launch without complex process management
"""

import sys
import os
from pathlib import Path

def main():
    # Set working directory and paths
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Add src to Python path
    src_path = script_dir / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    
    print("🚀 Starting GenAI OCR Chatbot...")
    print("📁 Working directory:", script_dir)
    
    # Import and run streamlit app directly
    try:
        import streamlit.web.cli as stcli
        streamlit_app_path = str(src_path / "ui" / "streamlit_app.py")
        
        # Set up streamlit arguments
        sys.argv = [
            "streamlit",
            "run",
            streamlit_app_path,
            "--server.port=8501",
            "--server.headless=true",
            "--browser.gatherUsageStats=false"
        ]
        
        print("🌐 Starting server at http://localhost:8501")
        stcli.main()
        
    except ImportError:
        print("❌ Streamlit not installed. Please run: pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
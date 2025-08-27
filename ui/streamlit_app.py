"""
Main Streamlit application for GenAI OCR Chatbot
Provides interfaces for both Phase 1 (OCR) and Phase 2 (Chatbot) functionality
"""

import streamlit as st
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Auto-configure Streamlit environment (cross-platform)
try:
    from src.ui.streamlit_config import setup_streamlit_environment
    # Only run setup if this is the main process (not during reloads)
    if not hasattr(st, '_streamlit_config_setup_done'):
        setup_streamlit_environment()
        st._streamlit_config_setup_done = True
except Exception as e:
    print(f"Warning: Streamlit auto-configuration failed: {e}")

# Set up logging (console only for now)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

from phase1_ui import render_phase1
from phase2_ui import render_phase2

def main():
    """Main application entry point"""
    
    # Page configuration
    st.set_page_config(
        page_title="GenAI OCR Chatbot",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # App header
    st.title("🤖 GenAI OCR Chatbot")
    st.markdown("**Azure OpenAI-powered Document Processing and Medical Services Assistant**")
    
    # Sidebar for navigation
    with st.sidebar:
        st.header("Navigation")
        st.markdown("---")
        
        st.markdown("---")
        
        # Phase selection
        phase = st.radio(
            "Select Phase:",
            ["Phase 1: OCR Field Extraction", "Phase 2: Medical Chatbot"],
            index=0
        )
        
        st.markdown("---")
        
        # Project info
        with st.expander("ℹ️ About This Project"):
            st.markdown("""
            **Assignment**: GenAI Developer Assessment
            
            **Phase 1**: Extract fields from National Insurance forms using OCR and Azure OpenAI
            
            **Phase 2**: Microservice-based chatbot for medical services Q&A
            
            **Technologies**: 
            - Azure OpenAI (GPT-4o, GPT-4o Mini)
            - Azure Document Intelligence
            - Streamlit UI
            - Native Python (no LangChain)
            """)
    
    # Main content area
    if phase == "Phase 1: OCR Field Extraction":
        render_phase1(demo_mode=False)  # Always production mode
    else:
        render_phase2(demo_mode=False)  # Always production mode
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666;'>"
        "GenAI OCR Chatbot | Powered by Azure OpenAI"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
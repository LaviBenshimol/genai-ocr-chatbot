"""
Main Streamlit application for GenAI OCR Chatbot
Provides interfaces for both Phase 1 (OCR) and Phase 2 (Chatbot) functionality
"""

import streamlit as st
import sys
import logging
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Streamlit auto-configuration removed - no longer needed

# Set up logging (console only for now)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

from phase1_ui import render_phase1
from phase2_ui import render_phase2
from analytics_ui import render_analytics_page
from api_client import MicroserviceClient

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
            ["Phase 1: OCR Field Extraction", "Phase 2: Medical Chatbot", "Analytics Dashboard"],
            index=0
        )
        
        # Project info
        with st.expander("ℹ️ About This Project"):
            st.markdown("""
            **Assignment**: GenAI Developer Assessment
            
            **Phase 1**: Extract fields from National Insurance forms using OCR and Azure OpenAI
            
            **Phase 2**: Microservice-based chatbot for medical services Q&A
            
            **Phase 3**: Analytics dashboard with interactive visualizations
            
            **Technologies**: 
            - Azure OpenAI (GPT-4o, GPT-4o Mini)
            - Azure Document Intelligence
            - ChromaDB Vector Database
            - Streamlit UI + Analytics Dashboard
            - Native Python (no LangChain)
            """)
        
        # Service Status at the BOTTOM of navigation
        st.markdown("---")
        st.markdown("**🔧 Service Status:**")
        
        current_time = time.time()
        
        # Initialize health check on first load
        if 'last_health_check' not in st.session_state:
            st.session_state.last_health_check = 0
            st.session_state.health_status_cache = {}
        
        # Only check health if it's been 7+ seconds since last check AND we have an empty cache
        time_since_last = current_time - st.session_state.last_health_check
        if time_since_last > 7 or not st.session_state.health_status_cache:
            api_client = MicroserviceClient()
            st.session_state.health_status_cache = api_client.check_services_health()
            st.session_state.last_health_check = current_time
        
        health_status = st.session_state.health_status_cache
        
        # Compact status display - 2x2 grid
        status_col1, status_col2 = st.columns(2)
        
        with status_col1:
            ocr_healthy = "healthy" in health_status.get("health-form-di-service", "")
            st.write("OCR: " + ("✅" if ocr_healthy else "❌"))
            
            chat_v2_healthy = "healthy" in health_status.get("chat-service-v2", "")
            st.write("Chat: " + ("✅" if chat_v2_healthy else "❌"))
        
        with status_col2:
            metrics_healthy = "healthy" in health_status.get("metrics-service", "")
            st.write("Metrics: " + ("✅" if metrics_healthy else "❌"))
            
            chromadb_ok = "chunks" in health_status.get("chromadb", "") or "loaded" in health_status.get("chromadb", "")
            st.write("DB: " + ("✅" if chromadb_ok else "⚠️"))
        
        # Show last check time
        if st.session_state.last_health_check > 0:
            secs_ago = int(current_time - st.session_state.last_health_check)
            if secs_ago < 60:
                st.caption(f"Updated {secs_ago}s ago")
            else:
                mins_ago = int(secs_ago / 60)
                st.caption(f"Updated {mins_ago}m ago")
        
        # Debug: Add a manual refresh button
        if st.button("🔄 Force Refresh", key="manual_health_refresh", help="Force refresh health status"):
            api_client = MicroserviceClient()
            st.session_state.health_status_cache = api_client.check_services_health()
            st.session_state.last_health_check = current_time
            st.rerun()
    
    # Main content area
    if phase == "Phase 1: OCR Field Extraction":
        render_phase1(demo_mode=False)  # Always production mode
    elif phase == "Phase 2: Medical Chatbot":
        render_phase2(demo_mode=False)  # Always production mode
    else:
        render_analytics_page()  # New analytics dashboard
    
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
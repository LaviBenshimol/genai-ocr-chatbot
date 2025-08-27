"""
Phase 2 UI: Medical Services Chatbot Interface
Handles chat conversations with the medical services knowledge base
Uses stateless chat-service microservice
"""

import streamlit as st
import json
import logging
from pathlib import Path
import sys

# Add project paths
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from api_client import MicroserviceClient

logger = logging.getLogger(__name__)

def render_phase2(demo_mode=False):
    """Render Phase 2 Chat interface with Flask API integration."""
    
    st.header("💬 Phase 2: Medical Services Chatbot")
    st.markdown("Ask questions about Israeli health insurance benefits and medical services using **stateless microservice architecture**")
    
    # Initialize API client
    api_client = MicroserviceClient()
    
    # Check services health
    health_status = api_client.check_services_health()
    
    # Check V2 chat service first, then V1 fallback
    chat_v2_status = health_status.get("chat-service-v2", "unknown")
    chat_v1_status = health_status.get("chat-service", "unknown")
    
    chat_service_healthy = "healthy" in chat_v2_status or "healthy" in chat_v1_status
    use_v2 = "healthy" in chat_v2_status
    
    # Store in session state for use throughout the session
    st.session_state.use_chat_v2 = use_v2
    
    if not chat_service_healthy:
        st.warning("⚠️ Chat service appears to be offline.")
        if use_v2:
            st.info("Please ensure the V2 chat microservice is running on port 5002")
        else:
            st.info("Please ensure the chat microservice is running on port 5000 or 5002")
        return
        
    # Show which version we're using
    if use_v2:
        st.success("✅ Using Chat Service V2 (Enhanced)")
    else:
        st.info("ℹ️ Using Chat Service V1 (Fallback)")
    
    # Initialize session state for conversation
    if "phase2_messages" not in st.session_state:
        st.session_state.phase2_messages = []
    if "phase2_user_profile" not in st.session_state:
        st.session_state.phase2_user_profile = {}
    
    # Create layout
    st.subheader("💬 Medical Services Assistant")
    
    # Language selection with session state
    if "phase2_language" not in st.session_state:
        st.session_state.phase2_language = "auto"
    
    language_options = ["auto", "he", "en"]
    format_map = {
        "auto": "🔄 Auto-detect (זיהוי אוטומטי)",
        "he": "Hebrew (עברית)", 
        "en": "English"
    }
    
    language = st.selectbox(
        "Select Language / בחר שפה:",
        language_options,
        format_func=lambda x: format_map[x],
        index=language_options.index(st.session_state.phase2_language),
        key="language_selector"
    )
    
    # Update session state when language changes
    if language != st.session_state.phase2_language:
        st.session_state.phase2_language = language
    
    # Show current language setting
    if language == "auto":
        st.info("🔄 Language will be auto-detected from your message")
    else:
        st.info(f"Language: {format_map[language]} ({language})")
    
    # Display current user profile if available
    if st.session_state.phase2_user_profile:
        with st.expander("👤 Your Profile"):
            profile_col1, profile_col2 = st.columns(2)
            with profile_col1:
                hmo = st.session_state.phase2_user_profile.get("hmo", "Unknown")
                st.write(f"**Health Fund:** {hmo}")
            with profile_col2:
                tier = st.session_state.phase2_user_profile.get("tier", "Unknown")
                st.write(f"**Membership Tier:** {tier}")
    
    # Chat interface
    chat_container = st.container()
    
    with chat_container:
        # Display conversation history
        for i, message in enumerate(st.session_state.phase2_messages):
            role = message.get("role", "user")
            content = message.get("content", "")
            
            if role == "user":
                with st.chat_message("user"):
                    st.write(content)
            else:
                with st.chat_message("assistant"):
                    st.write(content)
                    
                    # Show additional info if available
                    if "metadata" in message:
                        metadata = message["metadata"]
                        with st.expander("📊 Response Details"):
                            col_m1, col_m2, col_m3 = st.columns(3)
                            
                            with col_m1:
                                st.write(f"**Intent:** {metadata.get('intent', 'N/A')}")
                                st.write(f"**Action:** {metadata.get('action', 'N/A')}")
                            
                            with col_m2:
                                missing = metadata.get('missing_fields', [])
                                known = metadata.get('known_fields', {})
                                st.write(f"**Missing Fields:** {', '.join(missing) if missing else 'None'}")
                                st.write(f"**Known Fields:** {len(known)}")
                            
                            with col_m3:
                                tokens = metadata.get('token_usage', {})
                                context_metrics = metadata.get('context_metrics', {})
                                st.write(f"**Tokens Used:** {tokens.get('total_tokens', 0)}")
                                st.write(f"**KB Context:** {context_metrics.get('kb_context_chars', 0)} chars")
                                
                            # Show citations if available
                            citations = metadata.get('citations', [])
                            if citations:
                                st.write("**📚 Sources:**")
                                for citation in citations:
                                    st.write(f"- {citation}")
    
    # Chat input
    with st.container():
        user_input = st.chat_input("Ask about medical services... / שאל על שירותי הבריאות...")
        
        if user_input:
            # Add user message to conversation
            st.session_state.phase2_messages.append({
                "role": "user",
                "content": user_input
            })
            
            # Prepare conversation history for API
            conversation_history = []
            for msg in st.session_state.phase2_messages[:-1]:  # Exclude the current message
                conversation_history.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # Call chat service (V2 if available)
            with st.spinner("🤔 Thinking..."):
                try:
                    use_v2_service = st.session_state.get('use_chat_v2', False)
                    if use_v2_service:
                        result = api_client.chat_turn_v2(
                            message=user_input,
                            user_profile=st.session_state.phase2_user_profile,
                            conversation_history=conversation_history,
                            language=language
                        )
                    else:
                        result = api_client.chat_turn(
                            message=user_input,
                            user_profile=st.session_state.phase2_user_profile,
                            conversation_history=conversation_history,
                            language=language
                        )
                    
                    if result.get('success', True):  # Assume success if no explicit field
                        # Update user profile
                        updated_profile = result.get('updated_profile', {})
                        st.session_state.phase2_user_profile.update(updated_profile)
                        
                        # Get response
                        answer = result.get('answer', '')
                        next_question = result.get('next_question', '')
                        
                        # Use next_question if no answer
                        response_text = answer if answer else next_question
                        
                        if response_text:
                            # Add assistant response to conversation
                            st.session_state.phase2_messages.append({
                                "role": "assistant", 
                                "content": response_text,
                                "metadata": {
                                    "intent": result.get('intent', ''),
                                    "action": result.get('action', ''),
                                    "missing_fields": result.get('missing_fields', []),
                                    "known_fields": result.get('known_fields', {}),
                                    "token_usage": result.get('token_usage', {}),
                                    "context_metrics": result.get('context_metrics', {}),
                                    "citations": result.get('citations', [])
                                }
                            })
                        else:
                            st.error("No response received from chat service")
                    else:
                        error_msg = result.get('error', 'Unknown error')
                        st.error(f"❌ Chat Error: {error_msg}")
                        
                except Exception as e:
                    st.error(f"❌ Unexpected Error: {str(e)}")
                    logger.exception("Phase 2 chat error")
            
            # Rerun to show the new messages
            st.rerun()
    
    # Sidebar with conversation controls
    with st.sidebar:
        st.markdown("### 💬 Conversation Controls")
        
        if st.button("🗑️ Clear Conversation"):
            st.session_state.phase2_messages = []
            st.session_state.phase2_user_profile = {}
            st.rerun()
        
        if st.button("📤 Export Conversation"):
            conversation_data = {
                "messages": st.session_state.phase2_messages,
                "user_profile": st.session_state.phase2_user_profile,
                "language": language
            }
            st.download_button(
                label="💾 Download JSON",
                data=json.dumps(conversation_data, ensure_ascii=False, indent=2),
                file_name="medical_chat_conversation.json",
                mime="application/json"
            )
        
        # Show statistics
        if st.session_state.phase2_messages:
            st.markdown("### 📊 Statistics")
            user_msgs = len([m for m in st.session_state.phase2_messages if m["role"] == "user"])
            assistant_msgs = len([m for m in st.session_state.phase2_messages if m["role"] == "assistant"])
            st.write(f"**User Messages:** {user_msgs}")
            st.write(f"**Assistant Messages:** {assistant_msgs}")
            st.write(f"**Total Turns:** {user_msgs}")
            
            # Calculate total tokens if available
            total_tokens = 0
            for msg in st.session_state.phase2_messages:
                if "metadata" in msg:
                    tokens = msg["metadata"].get("token_usage", {})
                    total_tokens += tokens.get("total_tokens", 0)
            
            if total_tokens > 0:
                st.write(f"**Total Tokens:** {total_tokens:,}")

    # Instructions
    with st.expander("ℹ️ How to Use"):
        st.markdown("""
        **Phase 2 Medical Chatbot Instructions:**
        
        1. **Ask Questions**: Type questions about Israeli health insurance benefits
        2. **Provide Details**: The assistant will ask for your health fund (קופת חולים) and membership tier (מסלול)
        3. **Get Answers**: Once you provide the required information, you'll get personalized responses
        
        **Example Questions:**
        - "מה ההטבות לטיפולי שיניים?" (What are the dental benefits?)
        - "כמה עולה בדיקת עיניים?" (How much does an eye exam cost?)
        - "איך להירשם לסדנת הכנה ללידה?" (How to register for a childbirth preparation workshop?)
        
        **Supported Health Funds:** מכבי, מאוחדת, כללית
        **Supported Tiers:** זהב, כסף, ארד
        """)

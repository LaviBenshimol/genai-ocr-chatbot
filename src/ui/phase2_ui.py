"""
Phase 2 UI: Medical Services Chatbot Interface
Handles user information collection and medical Q&A
"""

import streamlit as st
import json
import time
from datetime import datetime
from pathlib import Path
import sys

# Add project paths
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def render_phase2(demo_mode=True):
    """Render Phase 2 chatbot interface"""
    
    st.header("💬 Phase 2: Medical Services Chatbot")
    st.markdown("AI assistant for Israeli health funds (Maccabi, Meuhedet, Clalit) medical services")
    
    # Initialize session state
    if 'chat_phase' not in st.session_state:
        st.session_state.chat_phase = 'info_collection'  # 'info_collection' or 'qa_session'
    if 'user_info' not in st.session_state:
        st.session_state.user_info = {}
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []
    
    # Sidebar for user information and settings
    with st.sidebar:
        st.subheader("👤 User Information")
        
        if st.session_state.chat_phase == 'info_collection':
            st.info("🔄 Currently collecting user information")
        else:
            # Display collected user info
            if st.session_state.user_info:
                with st.expander("📋 Collected Information"):
                    for key, value in st.session_state.user_info.items():
                        st.write(f"**{key}**: {value}")
                
                if st.button("🔄 Restart Information Collection"):
                    reset_chat_session()
        
        # Language selection
        st.subheader("🌐 Language")
        language = st.selectbox("Chat Language", ["Hebrew", "English"], index=0)
        
        # Reset button
        st.markdown("---")
        if st.button("🗑️ Reset Chat", type="secondary"):
            reset_chat_session()
    
    # Main chat area
    if st.session_state.chat_phase == 'info_collection':
        render_info_collection_phase(demo_mode, language)
    else:
        render_qa_phase(demo_mode, language)

def render_info_collection_phase(demo_mode, language):
    """Render user information collection interface"""
    
    st.subheader("📝 User Information Collection")
    st.markdown("The AI assistant will collect your personal and medical information for personalized service.")
    
    # Initialize with welcome message if no messages
    if not st.session_state.chat_messages:
        welcome_msg = get_welcome_message(language)
        st.session_state.chat_messages.append({
            "role": "assistant",
            "content": welcome_msg,
            "timestamp": datetime.now()
        })
    
    # Chat interface
    chat_container = st.container()
    
    with chat_container:
        # Display chat messages
        for message in st.session_state.chat_messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
                if "timestamp" in message:
                    st.caption(f"🕒 {message['timestamp'].strftime('%H:%M:%S')}")
    
    # User input for information collection
    user_input = st.chat_input("Type your response...")
    
    if user_input:
        # Add user message
        st.session_state.chat_messages.append({
            "role": "user", 
            "content": user_input,
            "timestamp": datetime.now()
        })
        
        # Process input and get AI response
        with st.spinner("🤖 Processing..."):
            time.sleep(1)  # Simulate processing
            
            if demo_mode:
                response, user_info_complete = process_info_collection_mock(
                    user_input, 
                    st.session_state.chat_messages,
                    language
                )
                
                # Add assistant response
                st.session_state.chat_messages.append({
                    "role": "assistant",
                    "content": response,
                    "timestamp": datetime.now()
                })
                
                # Check if information collection is complete
                if user_info_complete:
                    st.session_state.user_info = get_mock_user_info()
                    st.session_state.chat_phase = 'qa_session'
                    st.rerun()
            else:
                st.error("🔴 Production mode not yet implemented")

def render_qa_phase(demo_mode, language):
    """Render Q&A session interface"""
    
    st.subheader("❓ Medical Services Q&A")
    st.markdown("Ask questions about your health fund's medical services and benefits.")
    
    # Initialize Q&A session
    if len(st.session_state.conversation_history) == 0:
        transition_msg = get_transition_message(language, st.session_state.user_info)
        st.session_state.conversation_history.append({
            "role": "assistant",
            "content": transition_msg,
            "timestamp": datetime.now()
        })
    
    # Display conversation
    for message in st.session_state.conversation_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if "timestamp" in message:
                st.caption(f"🕒 {message['timestamp'].strftime('%H:%M:%S')}")
    
    # User input for Q&A
    question = st.chat_input("Ask about medical services...")
    
    if question:
        # Add user question
        st.session_state.conversation_history.append({
            "role": "user",
            "content": question,
            "timestamp": datetime.now()
        })
        
        # Process question and get answer
        with st.spinner("🔍 Searching knowledge base..."):
            time.sleep(2)  # Simulate processing
            
            if demo_mode:
                answer = process_qa_mock(
                    question,
                    st.session_state.user_info,
                    language
                )
                
                st.session_state.conversation_history.append({
                    "role": "assistant",
                    "content": answer,
                    "timestamp": datetime.now()
                })
                
                st.rerun()
            else:
                st.error("🔴 Production mode not yet implemented")

def reset_chat_session():
    """Reset the chat session to start over"""
    st.session_state.chat_phase = 'info_collection'
    st.session_state.user_info = {}
    st.session_state.chat_messages = []
    st.session_state.conversation_history = []

def get_welcome_message(language):
    """Get welcome message based on language"""
    if language == "Hebrew":
        return """שלום! 👋 אני עוזר AI שיעזור לך לקבל מידע על שירותי הבריאות של קופת החולים שלך.

כדי להתאים את השירות לצרכים שלך, אני צריך לאסוף כמה פרטים:
• שם פרטי ומשפחה
• מספר זהות (9 ספרות)
• מין וגיל
• קופת חולים (מכבי/מאוחדת/כללית)
• מספר חבר בקופה
• דרגת ביטוח (זהב/כסף/ארד)

בואו נתחיל - איך אוכל לקרוא לך?"""
    else:
        return """Hello! 👋 I'm an AI assistant that will help you get information about your health fund's medical services.

To customize the service for your needs, I need to collect some details:
• First and last name
• ID number (9 digits)
• Gender and age
• Health fund (Maccabi/Meuhedet/Clalit)
• Health fund member number
• Insurance tier (Gold/Silver/Bronze)

Let's start - what's your name?"""

def get_transition_message(language, user_info):
    """Get message for transitioning to Q&A phase"""
    name = user_info.get('name', 'Friend')
    hmo = user_info.get('hmo', 'your health fund')
    tier = user_info.get('tier', 'your insurance tier')
    
    if language == "Hebrew":
        return f"""תודה {name}! ✅ 

קלטתי את הפרטים שלך:
• קופת חולים: {hmo}
• דרגת ביטוח: {tier}

עכשיו אני מוכן לענות על שאלות לגבי השירותים הרפואיים שלך. אתה יכול לשאול על:
• טיפולים ברפואה משלימה (דיקור, שיאצו, רפלקסולוגיה וכו')
• שירותי רופא שיניים
• שירותי אופטומטריה
• שירותי הריון ולידה
• סדנאות בריאות
• ועוד...

מה תרצה לדעת?"""
    else:
        return f"""Thank you {name}! ✅

I've recorded your details:
• Health fund: {hmo}
• Insurance tier: {tier}

Now I'm ready to answer questions about your medical services. You can ask about:
• Alternative medicine treatments (acupuncture, shiatsu, reflexology, etc.)
• Dental services
• Optometry services
• Pregnancy and birth services
• Health workshops
• And more...

What would you like to know?"""

def process_info_collection_mock(user_input, chat_history, language):
    """Mock processing of information collection"""
    
    # Simple mock logic based on conversation length
    message_count = len([msg for msg in chat_history if msg["role"] == "user"])
    
    responses_hebrew = [
        "נהדר! עכשיו, תוכל לספר לי את מספר הזהות שלך? (9 ספרות)",
        "תודה. איזה גיל יש לך?",
        "באיזו קופת חולים אתה מבוטח? (מכבי/מאוחדת/כללית)",
        "מה דרגת הביטוח שלך? (זהב/כסף/ארד)",
        "מעולה! עכשיו יש לי את כל הפרטים שאני צריך. בואו ניתחיל עם השאלות שלך!"
    ]
    
    responses_english = [
        "Great! Now, can you tell me your ID number? (9 digits)",
        "Thank you. How old are you?",
        "Which health fund are you with? (Maccabi/Meuhedet/Clalit)",
        "What's your insurance tier? (Gold/Silver/Bronze)",
        "Excellent! Now I have all the details I need. Let's start with your questions!"
    ]
    
    responses = responses_hebrew if language == "Hebrew" else responses_english
    
    if message_count < len(responses):
        return responses[message_count], False
    else:
        return responses[-1], True

def process_qa_mock(question, user_info, language):
    """Mock processing of Q&A questions"""
    
    question_lower = question.lower()
    hmo = user_info.get('hmo', 'כללית')
    tier = user_info.get('tier', 'זהב')
    
    # Mock responses based on keywords
    if any(word in question_lower for word in ['דיקור', 'אקופונקטורה', 'acupuncture']):
        if language == "Hebrew":
            return f"""לגבי טיפולי דיקור סיני ב{hmo}:

**דרגת {tier}:**
• הנחה של 80% על טיפולים
• עד 16 טיפולים בשנה
• טלפון להזמנה: 2700*

הטיפול מתבצע על ידי מטפלים מוסמכים ויעיל לטיפול בכאבים, לחץ ועוד.

האם תרצה פרטים נוספים על טיפולים אחרים?"""
        else:
            return f"""Regarding acupuncture treatments at {hmo}:

**{tier} tier:**
• 80% discount on treatments
• Up to 16 treatments per year
• Appointment phone: 2700*

Treatment is performed by certified therapists and effective for pain, stress and more.

Would you like more details about other treatments?"""
    
    elif any(word in question_lower for word in ['שיניים', 'dental', 'dentist']):
        if language == "Hebrew":
            return f"""שירותי רופא שיניים ב{hmo}:

**דרגת {tier}:**
• בדיקה וטיפולי מניעה: כיסוי מלא
• סתימות: הנחה של 70%
• ציפוי שיניים: הנחה של 50%
• השתלות: הנחה של 30%

להזמנת תור: 2700* שלוחה 5

האם יש טיפול שיניים ספציפי שמעניין אותך?"""
    
    else:
        # Generic response
        if language == "Hebrew":
            return f"""תודה על השאלה! 

כמבוטח ב{hmo} בדרגת {tier}, יש לך גישה למגוון שירותים רפואיים.

אני יכול לעזור לך עם מידע על:
• רפואה משלימה (דיקור, שיאצו, רפלקסולוגיה)
• שירותי שיניים
• בדיקות עיניים ומשקפיים
• שירותי הריון
• סדנאות בריאות

אנא פרט יותר את השאלה שלך או בחר נושא ספציפי."""
        else:
            return f"""Thank you for your question!

As a member of {hmo} with {tier} tier, you have access to various medical services.

I can help you with information about:
• Alternative medicine (acupuncture, shiatsu, reflexology)
• Dental services  
• Eye exams and glasses
• Pregnancy services
• Health workshops

Please specify your question more or choose a specific topic."""

def get_mock_user_info():
    """Return mock user information"""
    return {
        "name": "יוסי כהן",
        "id": "123456789", 
        "age": "35",
        "gender": "זכר",
        "hmo": "כללית",
        "member_number": "987654321",
        "tier": "זהב"
    }
"""
Enhanced Grounded Answer Generation V2
Improved answer generation with fallback handling and better context formatting
"""
import os
import json
from typing import Dict, List, Any, Optional
from openai import AzureOpenAI
import logging

logger = logging.getLogger(__name__)


def _client() -> AzureOpenAI:
    return AzureOpenAI(
        azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
        api_key=os.environ.get("AZURE_OPENAI_API_KEY", ""),
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION") or "2024-10-21",
    )


def format_kb_context_for_llm(snippets: List[Dict[str, Any]]) -> str:
    """Format KB snippets into structured context for LLM"""
    
    if not snippets:
        return ""
    
    context_lines = ["מידע רלוונטי מבסיס הנתונים:"]
    context_lines.append("=" * 50)
    
    for i, snippet in enumerate(snippets, 1):
        metadata = snippet.get("metadata", {})
        content = snippet.get("content", "")
        
        context_lines.append(f"\\n{i}. קטגוריה: {metadata.get('category', 'לא מוגדר')}")
        if metadata.get('service'):
            context_lines.append(f"   שירות: {metadata.get('service')}")
        if metadata.get('fund'):
            context_lines.append(f"   קופת חולים: {metadata.get('fund')}")
        if metadata.get('plan'):
            context_lines.append(f"   מסלול: {metadata.get('plan')}")
        
        context_lines.append(f"   תוכן: {content}")
        context_lines.append("-" * 30)
    
    return "\\n".join(context_lines)


def generate_grounded_answer_v2(
    user_question: str,
    user_profile: Dict[str, Any],
    kb_context: str,
    conversation_history: List[Dict[str, str]],
    language: str = "he",
    answer_type: str = "specific_benefits",
    category: str = "",
    fallback_used: bool = False,
    max_tokens: int = 1200
) -> Dict[str, Any]:
    """
    Generate enhanced grounded answer with better handling of different scenarios
    """
    
    hmo = user_profile.get('hmo', '')
    tier = user_profile.get('tier', '')
    
    # Build enhanced system prompt based on answer type and context
    if fallback_used:
        system_prompt = f"""
אתה עוזר מידע לביטוח בריאות ישראלי מומחה ומועיל.

משימה: מספק מידע כללי על כל ההטבות הזמינות בקטגוריה "{category}" כי לא נמצא מידע ספציפי.

הנחיות חשובות:
1. הסבר שמציג מידע כללי על כל האפשרויות הזמינות בקטגוריה
2. ארגן את המידע בצורה ברורה לפי קופות חולים ומסלולים אם זמין
3. הדגש ההבדלים בין קופות החולים והמסלולים השונים
4. המלץ לבדוק עם קופת החולים הספציפית לוידוא פרטים
5. השתמש בשפה ברורה ומובנת
6. אם יש מידע חלקי בלבד, ציין זאת בבירור

פורמט תשובה:
- התחל עם הסבר קצר שמציג מידע כללי
- ארגן לפי קופות חולים ומסלולים אם זמין
- סיים עם המלצה לבירור נוסף עם קופת החולים

דוגמה לפתיחה: "הנה מידע כללי על כל ההטבות הזמינות בתחום {category}:"
"""
    else:
        system_prompt = f"""
אתה עוזר מידע לביטוח בריאות ישראלי מומחה ומועיל.

משימה: מענה מדויק על בסיס המידע שסופק על שירותי בריאות.

הנחיות חשובות:
1. השתמש רק במידע שמופיע בהקשר שסופק
2. אם המידע עבור {hmo} {tier} זמין, התמקד בו
3. אם אין מידע ספציפי, הצג את המידע הכללי הזמין
4. ציין במפורש אם המידע כללי או ספציפי למסלול
5. אל תמציא מידע שלא מופיע בהקשר
6. השתמש בשפה ברורה ומובנת
7. כלול המלצה לבירור נוסף עם קופת החולים אם נדרש

פורמט תשובה:
- תשובה ישירה לשאלה
- פירוט הטבות ספציפיות אם זמינות  
- הסבר על תנאים והגבלות אם רלוונטי
- המלצה לבירור נוסף אם נדרש
"""

    # Create conversation context
    recent_history = conversation_history[-4:] if conversation_history else []
    history_text = ""
    if recent_history:
        history_lines = []
        for turn in recent_history:
            role = "משתמש" if turn.get("role") == "user" else "עוזר"
            content = turn.get("content", "")
            history_lines.append(f"{role}: {content}")
        history_text = "\\n".join(history_lines)

    # Build user message
    user_message_parts = [f"שאלת המשתמש: {user_question}"]
    
    if hmo or tier:
        profile_text = f"פרופיל המשתמש: קופת חולים {hmo if hmo else 'לא מוגדר'}, מסלול {tier if tier else 'לא מוגדר'}"
        user_message_parts.append(profile_text)
    
    if history_text:
        user_message_parts.append(f"\\nהיסטוריית שיחה:\\n{history_text}")
    
    user_message_parts.append(f"\\nמידע רלוונטי:\\n{kb_context}")
    
    if fallback_used:
        user_message_parts.append(f"\\nהערה: מוצג מידע כללי כי לא נמצא מידע ספציפי עבור הפרופיל המבוקש.")

    user_message = "\\n\\n".join(user_message_parts)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]

    try:
        client = _client()
        response = client.chat.completions.create(
            model=os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
            messages=messages,
            temperature=0.3,  # Slightly higher for more natural responses
            max_tokens=max_tokens,
            top_p=0.9,
            frequency_penalty=0.1,  # Slight penalty to avoid repetition
            presence_penalty=0.1    # Encourage diverse explanations
        )

        answer = response.choices[0].message.content or ""
        
        # Add fallback indicator if used
        if fallback_used and answer:
            if language == "he":
                answer = f"📋 מידע כללי זמין:\\n\\n{answer}\\n\\n💡 לקבלת מידע מדויק יותר עבור המסלול שלך, מומלץ לפנות ישירות לקופת החולים שלך."
            else:
                answer = f"📋 General information available:\\n\\n{answer}\\n\\n💡 For more specific information about your plan, we recommend contacting your health fund directly."

        return {
            "answer": answer,
            "token_usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            "fallback_used": fallback_used,
            "answer_type": answer_type
        }

    except Exception as e:
        logger.error(f"Error generating grounded answer: {e}")
        
        # Fallback error response
        if language == "he":
            fallback_answer = "מצטער, אירעה שגיאה ביצירת התשובה. אנא נסה שוב או פנה לקופת החולים שלך ישירות."
        else:
            fallback_answer = "Sorry, an error occurred while generating the answer. Please try again or contact your health fund directly."
        
        return {
            "answer": fallback_answer,
            "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "fallback_used": True,
            "answer_type": "error",
            "error": str(e)
        }


def generate_collection_response(
    missing_fields: List[str],
    question_to_ask: str,
    alternative_offer: str,
    language: str = "he",
    politeness_level: str = "high"
) -> str:
    """
    Generate polite information collection response
    """
    
    if language == "he":
        if politeness_level == "high":
            response = f"שלום! אשמח לעזור לך. {question_to_ask}"
            if alternative_offer:
                response += f"\\n\\n{alternative_offer}"
            return response
        else:
            return question_to_ask
    else:
        if politeness_level == "high":
            response = f"Hello! I'd be happy to help you. {question_to_ask}"
            if alternative_offer:
                response += f"\\n\\n{alternative_offer}"
            return response
        else:
            return question_to_ask


def generate_scope_explanation(
    service_scope: str,
    available_services: List[str],
    language: str = "he"
) -> str:
    """
    Generate explanation when service is out of scope
    """
    
    if language == "he":
        if service_scope == "out_of_scope":
            services_text = ", ".join(available_services)
            return f"מצטער, השירות שביקשת אינו זמין במערכת המידע שלנו. השירותים הזמינים הם: {services_text}. אשמח לעזור לך באחד מהשירותים הזמינים."
        else:
            return "אשמח לעזור לך עם השירותים הזמינים במערכת."
    else:
        if service_scope == "out_of_scope":
            services_text = ", ".join(available_services)
            return f"Sorry, the service you requested is not available in our information system. Available services are: {services_text}. I'd be happy to help you with one of the available services."
        else:
            return "I'd be happy to help you with the available services in our system."

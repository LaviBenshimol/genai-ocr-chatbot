"""


Stage 1: Information Extractor
Extracts user information and classifies questions using focused LLM calls.
"""
import os
import json
from typing import Dict, List, Any, Optional
from openai import AzureOpenAI


def _client() -> AzureOpenAI:
    return AzureOpenAI(
        azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
        api_key=os.environ.get("AZURE_OPENAI_API_KEY", ""),
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION") or "2024-10-21",
    )


def extract_user_info_and_classify(
    message: str, 
    user_profile: Dict[str, Any], 
    conversation_history: List[Dict[str, str]], 
    language: str
) -> Dict[str, Any]:
    """
    Extract user information and classify the question type.
    Returns structured info about what we know and what KB context we need.
    """
    
    system_prompt = f"""
You are an information extractor for Israeli health insurance questions.

TASK: Extract user information and classify the health question.

AVAILABLE HEALTH SERVICES:
- מרפאות שיניים (Dental): בדיקות וניקוי, סתימות, טיפולי שורש, כתרים ושתלים
- אופטומטריה (Optometry): בדיקות עיניים, משקפיים, עדשות מגע  
- רפואה משלימה (Alternative): דיקור סיני, הומיאופתיה, נטורופתיה
- שירותי הריון (Pregnancy): ליווי הריון, הכנה ללידה, יעוץ הנקה
- מרפאות תקשורת (Communication): טיפול בדיבור, טיפול בשמיעה
- סדנאות (Workshops): סדנאות בריאות, הרצאות

USER INFO TO EXTRACT:
- hmo: מכבי | מאוחדת | כללית (health fund)
- tier: זהב | כסף | ארד (membership level)

OUTPUT FORMAT (JSON):
{{
  "extracted_info": {{
    "hmo": "string or null",
    "tier": "string or null"
  }},
  "question_classification": {{
    "category": "מרפאות שיניים | אופטומטריה | רפואה משלימה | שירותי הריון | מרפאות תקשורת | סדנאות | כללי | אחר",
    "intent": "specific_benefits | general_info | eligibility | cost_coverage | process_steps | other",
    "keywords": ["list", "of", "relevant", "keywords"]
  }},
  "information_status": {{
    "has_required_info": boolean,
    "missing_fields": ["array", "of", "missing", "fields"],
    "can_answer": boolean
  }},
  "next_action": {{
    "action": "collect_info | retrieve_answer",
    "question_to_ask": "string or null",
    "kb_query_needed": "string describing what KB context to retrieve"
  }}
}}

RULES:
1. Extract hmo/tier from current message AND conversation history
2. For specific benefits questions, you need BOTH hmo AND tier
3. For general information, you can answer without user details
4. Respond in {language}
5. Only ask for missing information that's actually needed
6. If question is not about health insurance, set category to "אחר"
7. IMPORTANT: Only return extracted_info fields that are NEW or mentioned in current message - do NOT return null for existing fields

IMPORTANT: 
- "category" = WHICH SERVICE TYPE (אופטומטריה for eye/vision, מרפאות שיניים for dental, etc.)
- "intent" = WHAT THEY WANT TO KNOW (specific_benefits, general_info, etc.)

EXAMPLES:
Input: "מה ההטבות לטיפולי שיניים?"
Output: category="מרפאות שיניים", intent="specific_benefits", missing hmo+tier, action=collect_info

Input: "מה טיפולי עיניים או אופטומטריה?"
Output: category="אופטומטריה", intent="specific_benefits", missing hmo+tier, action=collect_info

Input: "מה ההטבות לטיפולי שיניים במכבי זהב?"  
Output: category="מרפאות שיניים", intent="specific_benefits", has both, action=retrieve_answer
"""

    # Prepare input data
    input_data = {
        "current_message": message,
        "language": language,
        "existing_profile": user_profile,
        "conversation_history": conversation_history[-6:]  # Last 6 turns
    }
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(input_data, ensure_ascii=False)}
    ]
    
    client = _client()
    response = client.chat.completions.create(
        model=os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
        messages=messages,
        temperature=0.1,
        max_tokens=400,
        response_format={"type": "json_object"}
    )
    
    try:
        result = json.loads(response.choices[0].message.content or "{}")
        
        # Add token usage
        result["token_usage"] = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
        
        # Ensure required structure
        result.setdefault("extracted_info", {})
        result.setdefault("question_classification", {})
        result.setdefault("information_status", {})
        result.setdefault("next_action", {})
        
        return result
        
    except (json.JSONDecodeError, KeyError) as e:
        # Fallback response
        return {
            "extracted_info": {"hmo": None, "tier": None},
            "question_classification": {"category": "אחר", "intent": "other", "keywords": []},
            "information_status": {"has_required_info": False, "missing_fields": ["hmo", "tier"], "can_answer": False},
            "next_action": {"action": "collect_info", "question_to_ask": "אנא ספר לי באיזו קופת חולים אתה חבר ומה המסלול שלך?", "kb_query_needed": ""},
            "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "error": str(e)
        }


def merge_user_profile(current_profile: Dict[str, Any], extracted_info: Dict[str, Any]) -> Dict[str, Any]:
    """Merge current profile with newly extracted information."""
    merged = current_profile.copy()
    
    for key, value in extracted_info.items():
        if value and value.strip():  # Only update if we have a real value
            merged[key] = value.strip()
        # DO NOT overwrite existing values with null/empty
    
    return merged

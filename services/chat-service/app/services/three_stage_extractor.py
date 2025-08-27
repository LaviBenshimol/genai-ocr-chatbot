"""
Three-Stage LLM Pipeline for Medical Chat Service
Stage 1: Info Extraction
Stage 2: Category & Intent Classification  
Stage 3: Context Requirements & Action Determination
"""
import os
import json
from typing import Dict, List, Any, Optional
from openai import AzureOpenAI
import re


def _client() -> AzureOpenAI:
    return AzureOpenAI(
        azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
        api_key=os.environ.get("AZURE_OPENAI_API_KEY", ""),
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION") or "2024-10-21",
    )


def detect_language(message: str) -> str:
    """
    Simple language detection for Hebrew vs English.
    Returns 'he' for Hebrew, 'en' for English
    """
    if not message:
        return "he"  # Default to Hebrew
    
    # Count Hebrew characters (Unicode range 0590-05FF)
    hebrew_chars = len(re.findall(r'[\u0590-\u05FF]', message))
    # Count English letters
    english_chars = len(re.findall(r'[a-zA-Z]', message))
    
    # If more than 30% Hebrew characters, it's Hebrew
    total_chars = len(message.strip())
    if total_chars == 0:
        return "he"
    
    hebrew_ratio = hebrew_chars / total_chars
    english_ratio = english_chars / total_chars
    
    # Prioritize Hebrew since this is an Israeli service
    if hebrew_ratio > 0.2:  # 20% Hebrew threshold
        return "he"
    elif english_ratio > 0.5:  # 50% English threshold
        return "en"
    else:
        return "he"  # Default to Hebrew


def stage1_extract_user_info(
    message: str, 
    conversation_history: List[Dict[str, str]], 
    language: str
) -> Dict[str, Any]:
    """
    Stage 1: Extract user profile information from message and conversation history.
    Focus: Simple extraction, no reasoning.
    """
    
    system_prompt = f"""
You are a user information extractor for Israeli health insurance.

TASK: Extract user profile information from the message and conversation history.

FIELDS TO EXTRACT:
- hmo: מכבי | מאוחדת | כללית | null
- tier: זהב | כסף | ארד | null

RULES:
1. Look for health fund names in Hebrew or English
2. Look for membership tier/plan names
3. Only extract if explicitly mentioned
4. Return null if not found
5. Check both current message AND conversation history

OUTPUT (JSON):
{{
  "hmo": "string or null",
  "tier": "string or null"
}}

EXAMPLES:
Input: "אני במכבי זהב"
Output: {{"hmo": "מכבי", "tier": "זהב"}}

Input: "כמה עולה טיפול?"
Output: {{"hmo": null, "tier": null}}

Input: "אני חבר בכללית"
Output: {{"hmo": "כללית", "tier": null}}
"""

    input_data = {
        "current_message": message,
        "conversation_history": conversation_history[-6:],  # Last 6 turns
        "language": language
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
        max_tokens=200,
        response_format={"type": "json_object"}
    )
    
    try:
        result = json.loads(response.choices[0].message.content or "{}")
        result["token_usage"] = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
        return result
    except (json.JSONDecodeError, KeyError) as e:
        return {
            "hmo": None,
            "tier": None,
            "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "error": str(e)
        }


def stage2_classify_category_intent(
    message: str, 
    language: str
) -> Dict[str, Any]:
    """
    Stage 2: Classify service category and user intent.
    Focus: Clear classification with focused examples.
    """
    
    system_prompt = f"""
You are a precise classifier for Israeli health insurance questions.

TASK: Classify ONLY the service category and intent. Be very precise.

STEP 1: Look for KEYWORDS in the user's message:
- עיניים, אופטומטריה, משקפיים, עדשות, ראייה → "אופטומטריה"
- שיניים, דנטלי, ניקוי, סתימות → "מרפאות שיניים"  
- דיקור, הומיאופתיה, רפואה משלימה → "רפואה משלימה"
- הריון, לידה, הנקה → "שירותי הריון"
- דיבור, שמיעה, תקשורת → "מרפאות תקשורת"
- סדנה, הרצאה, קורס → "סדנאות"

STEP 2: Look for INTENT patterns:
- "מה ההטבות", "כיסוי", "הכיסוי", "הנחות", "תאונה", "שברתי", "בעיה" → "specific_benefits"
- "מה זה", "מה כולל", "מה זה אומר" → "general_info"
- "כמה עולה", "מחיר", "עלות", "תשלום" → "cost_coverage"
- "איך", "איך נרשמים", "תהליך", "איך מגישים" → "process_steps"

OUTPUT ONLY THIS JSON:
{{
  "category": "exact category name",
  "intent": "exact intent name", 
  "keywords": ["found", "keywords"]
}}

EXAMPLES:
"מה טיפולי עיניים או אופטומטריה?" 
→ {{"category": "אופטומטריה", "intent": "specific_benefits", "keywords": ["עיניים", "אופטומטריה"]}}

"מה ההטבות לטיפולי שיניים?"
→ {{"category": "מרפאות שיניים", "intent": "specific_benefits", "keywords": ["שיניים", "הטבות"]}}

"איך נרשמים לסדנה?"
→ {{"category": "סדנאות", "intent": "process_steps", "keywords": ["נרשמים", "סדנה"]}}
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Message: {message}\nLanguage: {language}"}
    ]
    
    client = _client()
    response = client.chat.completions.create(
        model=os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
        messages=messages,
        temperature=0.0,  # Deterministic for classification
        max_tokens=150,   # Shorter for focused classification
        top_p=0.1,        # Very focused sampling
        frequency_penalty=0.0,
        presence_penalty=0.0,
        response_format={"type": "json_object"}
    )
    
    try:
        result = json.loads(response.choices[0].message.content or "{}")
        result["token_usage"] = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
        return result
    except (json.JSONDecodeError, KeyError) as e:
        return {
            "category": "אחר",
            "intent": "other",
            "keywords": [],
            "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "error": str(e)
        }


def stage3_determine_action(
    message: str,
    user_profile: Dict[str, Any],
    category: str,
    intent: str,
    language: str
) -> Dict[str, Any]:
    """
    Stage 3: Determine what action to take based on context requirements.
    Focus: Business logic and flow control.
    """
    
    system_prompt = f"""
You are a context requirements analyzer for Israeli health insurance.

TASK: Determine if we have enough context to answer the question and what action to take.

CONTEXT REQUIREMENTS:
- For specific_benefits questions about services: NEED both HMO and tier
- For general_info questions: NO user details needed
- For process_steps questions: Usually need HMO, tier optional
- For cost_coverage questions: NEED both HMO and tier
- For eligibility questions: Usually need HMO, tier optional

AVAILABLE CATEGORIES: אופטומטריה, מרפאות שיניים, רפואה משלימה, שירותי הריון, מרפאות תקשורת, סדנאות

ACTIONS:
- collect_info: Need to ask for missing user information
- retrieve_answer: Have enough context to provide an answer

OUTPUT (JSON):
{{
  "has_required_info": boolean,
  "missing_fields": ["array of missing fields"],
  "can_answer": boolean,
  "action": "collect_info | retrieve_answer",
  "question_to_ask": "string or null",
  "reason": "explanation of decision"
}}

EXAMPLES:
Input: intent="specific_benefits", category="אופטומטריה", profile={{"hmo": null, "tier": null}}
Output: {{"has_required_info": false, "missing_fields": ["hmo", "tier"], "can_answer": false, "action": "collect_info", "question_to_ask": "באיזו קופת חולים אתה חבר ומה המסלול שלך?"}}

Input: intent="specific_benefits", category="אופטומטריה", profile={{"hmo": "מכבי", "tier": "זהב"}}  
Output: {{"has_required_info": true, "missing_fields": [], "can_answer": true, "action": "retrieve_answer", "question_to_ask": null}}

Input: intent="general_info", category="אופטומטריה", profile={{}}
Output: {{"has_required_info": true, "missing_fields": [], "can_answer": true, "action": "retrieve_answer", "question_to_ask": null}}
"""

    input_data = {
        "message": message,
        "user_profile": user_profile,
        "category": category,
        "intent": intent,
        "language": language
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
        max_tokens=300,
        response_format={"type": "json_object"}
    )
    
    try:
        result = json.loads(response.choices[0].message.content or "{}")
        result["token_usage"] = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
        return result
    except (json.JSONDecodeError, KeyError) as e:
        return {
            "has_required_info": False,
            "missing_fields": ["hmo", "tier"],
            "can_answer": False,
            "action": "collect_info",
            "question_to_ask": "אנא ספר לי באיזו קופת חולים אתה חבר ומה המסלול שלך?",
            "reason": f"Error: {str(e)}",
            "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "error": str(e)
        }


def three_stage_process(
    message: str,
    user_profile: Dict[str, Any], 
    conversation_history: List[Dict[str, str]], 
    language: str
) -> Dict[str, Any]:
    """
    Run the complete 3-stage pipeline with auto-language detection.
    """
    
    # Auto-detect language if needed
    if not language or language == "auto":
        detected_language = detect_language(message)
        print(f"Language auto-detected: {detected_language} for message: {message[:50]}...")
    else:
        detected_language = language
    
    # Stage 1: Extract user info
    stage1_result = stage1_extract_user_info(message, conversation_history, detected_language)
    
    # Merge with existing profile (don't overwrite with null)
    merged_profile = user_profile.copy()
    for key, value in stage1_result.items():
        if key not in ["token_usage", "error"] and value and str(value).strip():
            merged_profile[key] = str(value).strip()
    
    # Stage 2: Classify category and intent
    stage2_result = stage2_classify_category_intent(message, detected_language)
    
    # Stage 3: Determine action
    stage3_result = stage3_determine_action(
        message=message,
        user_profile=merged_profile,
        category=stage2_result.get("category", "אחר"),
        intent=stage2_result.get("intent", "other"),
        language=detected_language
    )
    
    # Combine results
    total_tokens = (
        stage1_result.get("token_usage", {}).get("total_tokens", 0) +
        stage2_result.get("token_usage", {}).get("total_tokens", 0) +
        stage3_result.get("token_usage", {}).get("total_tokens", 0)
    )
    
    return {
        "extracted_info": {k: v for k, v in stage1_result.items() if k not in ["token_usage", "error"]},
        "updated_profile": merged_profile,
        "classification": {
            "category": stage2_result.get("category", "אחר"),
            "intent": stage2_result.get("intent", "other"),
            "keywords": stage2_result.get("keywords", [])
        },
        "requirements": {
            "has_required_info": stage3_result.get("has_required_info", False),
            "missing_fields": stage3_result.get("missing_fields", []),
            "can_answer": stage3_result.get("can_answer", False),
            "action": stage3_result.get("action", "collect_info"),
            "question_to_ask": stage3_result.get("question_to_ask", ""),
            "reason": stage3_result.get("reason", "")
        },
        "token_usage": {
            "stage1_tokens": stage1_result.get("token_usage", {}),
            "stage2_tokens": stage2_result.get("token_usage", {}),
            "stage3_tokens": stage3_result.get("token_usage", {}),
            "total_tokens": total_tokens
        }
    }

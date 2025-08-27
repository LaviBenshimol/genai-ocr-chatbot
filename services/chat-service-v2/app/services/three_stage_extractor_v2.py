"""
Enhanced Three-Stage LLM Pipeline for Medical Chat Service V2
Stage 1: Info Extraction with Service Awareness
Stage 2: Category & Intent Classification with Service Scope Detection
Stage 3: Context Requirements & Action Determination with Polite Collection
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


def stage1_extract_user_info_v2(
    message: str, 
    conversation_history: List[Dict[str, str]], 
    language: str,
    available_services: Dict[str, List[str]]
) -> Dict[str, Any]:
    """
    Stage 1 V2: Extract user profile information with service awareness.
    Enhanced to understand context and provide better extraction.
    """
    
    # Create service descriptions for better context
    service_descriptions = ""
    for category, services in available_services.items():
        service_descriptions += f"- {category}: {', '.join(services[:3])}{'...' if len(services) > 3 else ''}\\n"
    
    system_prompt = f"""
You are an enhanced user information extractor for Israeli health insurance services.

AVAILABLE SERVICES:
{service_descriptions}

TASK: Extract user profile information from the message and conversation history.

FIELDS TO EXTRACT:
- hmo: מכבי | מאוחדת | כללית | null
- tier: זהב | כסף | ארד | null

ENHANCED RULES:
1. Look for health fund names in Hebrew or English (including variations like "Maccabi", "Clalit")
2. Look for membership tier/plan names (Gold = זהב, Silver = כסף, Bronze = ארד)
3. Check both current message AND full conversation history
4. Extract only if explicitly mentioned or strongly implied
5. Return null if not found or uncertain
6. Consider context clues (e.g., "my plan covers..." might indicate tier info)

OUTPUT (JSON):
{{
  "hmo": "string or null",
  "tier": "string or null",
  "confidence": "high|medium|low",
  "extracted_from": "current_message|history|context_clues"
}}

EXAMPLES:
Input: "אני במכבי זהב"
Output: {{"hmo": "מכבי", "tier": "זהב", "confidence": "high", "extracted_from": "current_message"}}

Input: "My Maccabi Gold plan covers dental"
Output: {{"hmo": "מכבי", "tier": "זהב", "confidence": "high", "extracted_from": "current_message"}}

Input: "כמה עולה טיפול?"
Output: {{"hmo": null, "tier": null, "confidence": "high", "extracted_from": "current_message"}}
"""

    input_data = {
        "current_message": message,
        "conversation_history": conversation_history[-10:],  # Last 10 turns for better context
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
            "confidence": "low",
            "extracted_from": "error",
            "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "error": str(e)
        }


def stage2_classify_category_intent_v2(
    message: str, 
    language: str,
    available_services: Dict[str, List[str]],
    conversation_history: List[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Stage 2 V2: Enhanced classification with service scope detection.
    """
    
    # Build available categories and services
    categories_list = []
    for category, services in available_services.items():
        service_sample = ", ".join(services[:2]) + ("..." if len(services) > 2 else "")
        categories_list.append(f"- {category}: {service_sample}")
    
    available_categories_text = "\\n".join(categories_list)
    
    # Extract conversation context for better classification
    conversation_context = ""
    if conversation_history:
        recent_turns = conversation_history[-4:]  # Last 4 turns for context
        context_lines = []
        for turn in recent_turns:
            role = turn.get("role", "")
            content = turn.get("content", "")
            if role and content:
                context_lines.append(f"{role}: {content}")
        if context_lines:
            conversation_context = f"\\n\\nCONVERSATION CONTEXT:\\n" + "\\n".join(context_lines)
    
    system_prompt = f"""
You are an enhanced classifier for Israeli health insurance questions.

AVAILABLE CATEGORIES AND SERVICES:
{available_categories_text}

TASK: Classify service category, intent, and determine if the request is within our service scope.

IMPORTANT: If this is a follow-up message (like "כללית", "מכבי", "זהב") that provides missing information,
look at the conversation context to understand the original intent and category.

STEP 1: KEYWORD ANALYSIS - Look for these patterns:
- עיניים, אופטומטריה, משקפיים, עדשות, ראייה → "אופטומטריה"
- שיניים, דנטלי, ניקוי, סתימות, כתרים → "מרפאות שיניים"  
- דיקור, הומיאופתיה, רפואה משלימה, אלטרנטיבי → "רפואה משלימה"
- הריון, לידה, הנקה, יולדת → "שירותי הריון"
- דיבור, שמיעה, תקשורת, לוגופד → "מרפאות תקשורת"
- סדנה, הרצאה, קורס, הדרכה → "סדנאות"

STEP 2: INTENT DETECTION:
- "מה ההטבות", "כיסוי", "הכיסוי", "הנחות" → "specific_benefits"
- "מה זה", "מה כולל", "הסבר", "מה זה אומר" → "general_info"
- "כמה עולה", "מחיר", "עלות", "תשלום" → "cost_coverage"
- "איך", "תהליך", "איך נרשמים", "איך מגישים" → "process_steps"

STEP 3: SCOPE DETECTION:
- in_scope: Question relates to available categories
- out_of_scope: Question about services we don't cover
- partial_scope: Question partially relates to our services

OUTPUT (JSON):
{{
  "category": "exact category name or 'אחר'",
  "intent": "specific_benefits|general_info|cost_coverage|process_steps|other", 
  "keywords": ["found", "keywords"],
  "confidence": "high|medium|low",
  "service_scope": "in_scope|out_of_scope|partial_scope",
  "scope_explanation": "why this scope was determined"
}}

EXAMPLES:
"מה ההטבות לטיפולי שיניים במכבי זהב?"
→ {{"category": "מרפאות שיניים", "intent": "specific_benefits", "keywords": ["הטבות", "שיניים"], "confidence": "high", "service_scope": "in_scope", "scope_explanation": "dental benefits are covered in our system"}}

"איך נרשמים לקורס יוגה?"
→ {{"category": "סדנאות", "intent": "process_steps", "keywords": ["נרשמים", "קורס"], "confidence": "medium", "service_scope": "partial_scope", "scope_explanation": "workshops are covered but yoga specifically may not be available"}}

"מה ההטבות לניתוחי לב?"
→ {{"category": "אחר", "intent": "specific_benefits", "keywords": ["הטבות", "ניתוחי", "לב"], "confidence": "high", "service_scope": "out_of_scope", "scope_explanation": "cardiac surgery is not in our available service categories"}}

FOLLOW-UP EXAMPLES (using conversation context):
If conversation shows:
user: "אילו הטבות יש לחבר מועדון זהב בטיפולי שיניים?"
assistant: "באיזו קופת חולים אתה חבר?"
Current message: "כללית"
→ {{"category": "מרפאות שיניים", "intent": "specific_benefits", "keywords": ["כללית"], "confidence": "high", "service_scope": "in_scope", "scope_explanation": "providing missing HMO info for dental benefits question"}}
"""

    user_content = f"Message: {message}\\nLanguage: {language}{conversation_context}"
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
    ]
    
    client = _client()
    response = client.chat.completions.create(
        model=os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
        messages=messages,
        temperature=0.1,  # Slightly higher for better reasoning
        max_tokens=200,
        top_p=0.2,        # More focused sampling
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
            "confidence": "low",
            "service_scope": "unknown",
            "scope_explanation": f"Error in classification: {str(e)}",
            "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "error": str(e)
        }


def stage3_determine_action_v2(
    message: str,
    user_profile: Dict[str, Any],
    category: str,
    intent: str,
    service_scope: str,
    language: str
) -> Dict[str, Any]:
    """
    Stage 3 V2: Enhanced action determination with polite information collection.
    """
    
    system_prompt = f"""
You are an enhanced context analyzer for Israeli health insurance services.

TASK: Determine action based on context requirements and provide polite, helpful responses.

ENHANCED CONTEXT REQUIREMENTS:
- For specific_benefits: NEED both HMO and tier for personalized information
- For general_info: NO user details needed (provide general overview)
- For process_steps: Usually need HMO (procedures may vary by fund)
- For cost_coverage: NEED both HMO and tier for accurate pricing
- For eligibility: Usually need HMO, tier helpful

SERVICE SCOPE HANDLING:
- in_scope: Proceed with normal flow
- out_of_scope: Politely explain what we do cover
- partial_scope: Offer what we can provide

AVAILABLE CATEGORIES: אופטומטריה, מרפאות שיניים, רפואה משלימה, שירותי הריון, מרפאות תקשורת, סדנאות

POLITE COLLECTION STRATEGY:
1. Be friendly and helpful
2. Explain WHY we need the information  
3. Offer to provide general information as alternative
4. Use encouraging language

ACTIONS:
- collect_info: Need to ask for missing user information (be polite!)
- retrieve_answer: Have enough context to provide an answer
- explain_scope: Service is out of scope, explain alternatives

OUTPUT (JSON):
{{
  "has_required_info": boolean,
  "missing_fields": ["array of missing fields"],
  "can_answer": boolean,
  "action": "collect_info | retrieve_answer | explain_scope",
  "question_to_ask": "string or null (polite question)",
  "alternative_offer": "string or null (what we can provide without personal info)",
  "reason": "explanation of decision",
  "politeness_level": "high|medium|standard"
}}

POLITE QUESTION EXAMPLES (Hebrew):
- "כדי לספק לך מידע מדויק על ההטבות, האם תוכל לשתף איתי באיזו קופת חולים אתה חבר ומה המסלול שלך? זה יעזור לי לתת לך תשובה מותאמת אישית."
- "אשמח לעזור לך! כדי לבדוק את הכיסוי הספציפי שלך, האם תוכל לציין את קופת החולים והמסלול? אם תעדיף, אוכל גם לספק מידע כללי."

ALTERNATIVE OFFERS (Hebrew):
- "בינתיים, אוכל לספק לך מידע כללי על השירות הזה."
- "אם תרצה, אוכל להסביר על השירות באופן כללי ללא פרטים אישיים."

EXAMPLES:
Input: intent="specific_benefits", category="אופטומטריה", profile={{"hmo": null, "tier": null}}, scope="in_scope"
Output: {{
  "has_required_info": false, 
  "missing_fields": ["hmo", "tier"], 
  "can_answer": false, 
  "action": "collect_info",
  "question_to_ask": "כדי לספק לך מידע מדויק על הטבות האופטומטריה, האם תוכל לשתף איתי באיזו קופת חולים אתה חבר ומה המסלול שלך?",
  "alternative_offer": "אם תעדיף, אוכל לספק מידע כללי על שירותי אופטומטריה ללא פרטים אישיים.",
  "reason": "Need HMO and tier for personalized benefits information",
  "politeness_level": "high"
}}

Input: intent="general_info", category="אופטומטריה", profile={{}}, scope="in_scope"
Output: {{
  "has_required_info": true, 
  "missing_fields": [], 
  "can_answer": true, 
  "action": "retrieve_answer",
  "question_to_ask": null,
  "alternative_offer": null,
  "reason": "General information doesn't require personal details",
  "politeness_level": "standard"
}}

Input: intent="specific_benefits", category="אחר", scope="out_of_scope"
Output: {{
  "has_required_info": false,
  "missing_fields": [],
  "can_answer": false,
  "action": "explain_scope",
  "question_to_ask": null,
  "alternative_offer": "אוכל לעזור לך עם שירותי אופטומטריה, מרפאות שיניים, רפואה משלימה, שירותי הריון, מרפאות תקשורת או סדנאות.",
  "reason": "Requested service is outside our available categories",
  "politeness_level": "high"
}}
"""

    input_data = {
        "message": message,
        "user_profile": user_profile,
        "category": category,
        "intent": intent,
        "service_scope": service_scope,
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
        temperature=0.2,  # Slightly higher for more natural language
        max_tokens=400,   # More space for polite responses
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
            "question_to_ask": "אנא ספר לי באיזו קופת חולים אתה חבר ומה המסלול שלך כדי שאוכל לעזור לך טוב יותר.",
            "alternative_offer": "אוכל לספק מידע כללי אם תעדיף.",
            "reason": f"Error: {str(e)}",
            "politeness_level": "high",
            "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "error": str(e)
        }


def three_stage_process_v2(
    message: str,
    user_profile: Dict[str, Any], 
    conversation_history: List[Dict[str, str]], 
    language: str,
    available_services: Dict[str, List[str]]
) -> Dict[str, Any]:
    """
    Run the enhanced 3-stage pipeline with service awareness and polite collection.
    """
    
    # Auto-detect language if needed
    if not language or language == "auto":
        detected_language = detect_language(message)
        print(f"Language auto-detected: {detected_language} for message: {message[:50]}...")
    else:
        detected_language = language
    
    # Stage 1: Enhanced user info extraction
    stage1_result = stage1_extract_user_info_v2(
        message, conversation_history, detected_language, available_services
    )
    
    # Merge with existing profile (don't overwrite with null)
    merged_profile = user_profile.copy()
    for key, value in stage1_result.items():
        if key not in ["token_usage", "error", "confidence", "extracted_from"] and value and str(value).strip():
            merged_profile[key] = str(value).strip()
    
    # Stage 2: Enhanced classification with service scope and conversation context
    stage2_result = stage2_classify_category_intent_v2(
        message, detected_language, available_services, conversation_history
    )
    
    # Stage 3: Enhanced action determination
    stage3_result = stage3_determine_action_v2(
        message=message,
        user_profile=merged_profile,
        category=stage2_result.get("category", "אחר"),
        intent=stage2_result.get("intent", "other"),
        service_scope=stage2_result.get("service_scope", "unknown"),
        language=detected_language
    )
    
    # Combine results with enhanced information
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
            "keywords": stage2_result.get("keywords", []),
            "confidence": stage2_result.get("confidence", "medium")
        },
        "service_scope": stage2_result.get("service_scope", "unknown"),
        "scope_explanation": stage2_result.get("scope_explanation", ""),
        "requirements": {
            "has_required_info": stage3_result.get("has_required_info", False),
            "missing_fields": stage3_result.get("missing_fields", []),
            "can_answer": stage3_result.get("can_answer", False),
            "action": stage3_result.get("action", "collect_info"),
            "question_to_ask": stage3_result.get("question_to_ask", ""),
            "alternative_offer": stage3_result.get("alternative_offer", ""),
            "reason": stage3_result.get("reason", ""),
            "politeness_level": stage3_result.get("politeness_level", "standard")
        },
        "token_usage": {
            "stage1_tokens": stage1_result.get("token_usage", {}),
            "stage2_tokens": stage2_result.get("token_usage", {}),
            "stage3_tokens": stage3_result.get("token_usage", {}),
            "total_tokens": total_tokens
        }
    }

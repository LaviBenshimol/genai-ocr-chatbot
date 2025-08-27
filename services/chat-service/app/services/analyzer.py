"""
Analyzer: single-turn controller using Azure OpenAI (GPT-4o).
Extracts/normalizes user info, detects intent and answer_type, and
returns gating info and next_question in strict JSON.
"""
import os
from typing import Dict, List, Any
from openai import AzureOpenAI


def _client() -> AzureOpenAI:
    return AzureOpenAI(
        azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
        api_key=os.environ.get("AZURE_OPENAI_API_KEY", ""),
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21"),
    )


def analyze_turn(message: str, user_profile: Dict[str, Any], history: List[Dict[str, str]], language: str) -> Dict[str, Any]:
    system = (
        "You are an Israeli medical benefits analyzer. Output strict JSON only.\n\n"
        
        "=== AVAILABLE SERVICES ===\n"
        "מרפאות שיניים: בדיקות וניקוי שיניים, סתימות, טיפולי שורש, כתרים ושתלים\n"
        "אופטומטריה: בדיקות עיניים, משקפיים, עדשות מגע\n"
        "רפואה משלימה: דיקור סיני, הומיאופתיה, נטורופתיה\n"
        "שירותי הריון: ליווי הריון, הכנה ללידה, יעוץ הנקה\n\n"
        
        "=== FIELD REQUIREMENTS BY QUESTION TYPE ===\n"
        "Dental questions (שיניים/שן/שיניים): EXACTLY hmo + tier\n"
        "Optometry questions (אופט/משקפ/עיניים): EXACTLY hmo + tier\n"
        "Alternative medicine (רפואה משלימה/דיקור): EXACTLY hmo + tier\n"
        "Pregnancy services (הריון/הנקה): EXACTLY hmo + tier\n"
        "ALL other medical questions: EXACTLY hmo + tier\n\n"
        
        "=== VALID VALUES ===\n"
        "hmo: MUST be exactly one of {מכבי, מאוחדת, כללית}\n"
        "tier: MUST be exactly one of {זהב, כסף, ארד}\n\n"
        
        "=== EXAMPLES WITH CONVERSATION HISTORY ===\n"
        
        "EXAMPLE 1 - First message, no profile:\n"
        "message: 'מה ההטבות לטיפולי שיניים?'\n"
        "user_profile: {}\n"
        "conversation_history: []\n"
        "OUTPUT: {\n"
        "  \"intent\": \"qa\",\n"
        "  \"answer_type\": \"specific_benefits\",\n"
        "  \"updated_profile\": {},\n"
        "  \"known_fields\": {},\n"
        "  \"missing_fields\": [\"hmo\", \"tier\"],\n"
        "  \"sufficient_context_for_answer\": false,\n"
        "  \"next_question\": \"באיזו קופת חולים אתה חבר ומה המסלול שלך?\"\n"
        "}\n\n"
        
        "EXAMPLE 2 - Second message, user provides HMO:\n"
        "message: 'אני במכבי'\n"
        "user_profile: {}\n"
        "conversation_history: [{\"role\": \"user\", \"content\": \"מה ההטבות לטיפולי שיניים?\"}, {\"role\": \"assistant\", \"content\": \"באיזו קופת חולים אתה חבר?\"}]\n"
        "OUTPUT: {\n"
        "  \"intent\": \"collection\",\n"
        "  \"answer_type\": \"specific_benefits\",\n"
        "  \"updated_profile\": {\"hmo\": \"מכבי\"},\n"
        "  \"known_fields\": {\"hmo\": \"מכבי\"},\n"
        "  \"missing_fields\": [\"tier\"],\n"
        "  \"sufficient_context_for_answer\": false,\n"
        "  \"next_question\": \"מה המסלול שלך במכבי - זהב, כסף או ארד?\"\n"
        "}\n\n"
        
        "EXAMPLE 3 - Third message, user provides tier:\n"
        "message: 'זהב'\n"
        "user_profile: {\"hmo\": \"מכבי\"}\n"
        "conversation_history: [{\"role\": \"user\", \"content\": \"מה ההטבות לטיפולי שיניים?\"}, {\"role\": \"assistant\", \"content\": \"באיזו קופת חולים?\"}, {\"role\": \"user\", \"content\": \"מכבי\"}, {\"role\": \"assistant\", \"content\": \"מה המסלול?\"}]\n"
        "OUTPUT: {\n"
        "  \"intent\": \"qa\",\n"
        "  \"answer_type\": \"specific_benefits\",\n"
        "  \"updated_profile\": {\"hmo\": \"מכבי\", \"tier\": \"זהב\"},\n"
        "  \"known_fields\": {\"hmo\": \"מכבי\", \"tier\": \"זהב\"},\n"
        "  \"missing_fields\": [],\n"
        "  \"sufficient_context_for_answer\": true,\n"
        "  \"next_question\": \"\"\n"
        "}\n\n"
        
        "EXAMPLE 4 - User provides both at once:\n"
        "message: 'מה ההטבות לטיפולי שיניים במכבי זהב?'\n"
        "user_profile: {}\n"
        "conversation_history: []\n"
        "OUTPUT: {\n"
        "  \"intent\": \"qa\",\n"
        "  \"answer_type\": \"specific_benefits\",\n"
        "  \"updated_profile\": {\"hmo\": \"מכבי\", \"tier\": \"זהב\"},\n"
        "  \"known_fields\": {\"hmo\": \"מכבי\", \"tier\": \"זהב\"},\n"
        "  \"missing_fields\": [],\n"
        "  \"sufficient_context_for_answer\": true,\n"
        "  \"next_question\": \"\"\n"
        "}\n\n"
        
        "=== CRITICAL RULES ===\n"
        "1. missing_fields is ALWAYS an array of strings like [\"hmo\", \"tier\"], NEVER an object like {\"hmo\": true}\n"
        "2. For dental questions, you need ONLY hmo + tier, NOT age/ID/anything else\n"
        "3. Extract hmo/tier from the current message or conversation history\n"
        "4. If you have both hmo + tier, set sufficient_context_for_answer = true\n"
        "5. Respond in the same language as the user's message\n"
        "6. Do NOT ask for extra fields like age/ID unless specifically needed for pregnancy services\n\n"
        
        "=== OUTPUT FORMAT ===\n"
        "Always return JSON with exactly these keys:\n"
        "intent, answer_type, updated_profile, known_fields, missing_fields, sufficient_context_for_answer, next_question"
    )

    schema_hint = (
        "Return JSON with keys: intent, answer_type, updated_profile, known_fields, missing_fields, sufficient_context_for_answer, next_question."
    )

    user_blob = {
        "message": message,
        "language": language,
        "user_profile": user_profile,
        "conversation_history": history[-8:],  # last 8 turns for brevity
    }

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"{schema_hint}\nINPUT:\n{user_blob}"},
    ]

    client = _client()
    resp = client.chat.completions.create(
        model=os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
        messages=messages,
        temperature=0.0,  # Make it more deterministic
        max_tokens=300,   # Shorter responses
        response_format={"type": "json_object"},
    )
    content = resp.choices[0].message.content or "{}"
    usage = resp.usage
    try:
        import json
        data = json.loads(content)
    except Exception:
        data = {}

    data.setdefault("token_usage", {"prompt_tokens": getattr(usage, "prompt_tokens", 0),
                                      "completion_tokens": getattr(usage, "completion_tokens", 0),
                                      "total_tokens": getattr(usage, "total_tokens", 0)})
    # Fallbacks and fixes
    data.setdefault("updated_profile", user_profile)
    data.setdefault("known_fields", {})
    data.setdefault("missing_fields", [])
    data.setdefault("sufficient_context_for_answer", False)
    data.setdefault("next_question", "")
    data.setdefault("intent", "other")
    data.setdefault("answer_type", "other")
    
    # FORCE CORRECT FORMAT: Convert missing_fields to array if it's an object
    missing_fields = data.get("missing_fields", [])
    if isinstance(missing_fields, dict):
        # Convert {"hmo": true, "tier": true} to ["hmo", "tier"]
        data["missing_fields"] = [k for k, v in missing_fields.items() if v]
    
    # FORCE CORRECT LOGIC: For dental questions, only need hmo+tier
    current_profile = data.get("updated_profile", {})
    
    # Also extract from current message and history
    all_text = message.lower()
    for h in history:
        all_text += " " + h.get("content", "").lower()
    
    # Extract HMO
    hmo_value = current_profile.get("hmo") or user_profile.get("hmo")
    if not hmo_value:
        if "מכבי" in all_text:
            hmo_value = "מכבי"
            current_profile["hmo"] = "מכבי"
        elif "מאוחדת" in all_text:
            hmo_value = "מאוחדת" 
            current_profile["hmo"] = "מאוחדת"
        elif "כללית" in all_text:
            hmo_value = "כללית"
            current_profile["hmo"] = "כללית"
    
    # Extract tier
    tier_value = current_profile.get("tier") or user_profile.get("tier")
    if not tier_value:
        if "זהב" in all_text:
            tier_value = "זהב"
            current_profile["tier"] = "זהב"
        elif "כסף" in all_text:
            tier_value = "כסף"
            current_profile["tier"] = "כסף"
        elif "ארד" in all_text:
            tier_value = "ארד"
            current_profile["tier"] = "ארד"
    
    data["updated_profile"] = current_profile
    has_hmo = bool(hmo_value)
    has_tier = bool(tier_value)
    
    # Check if this is a dental conversation (either current message or history)
    is_dental = "שיניים" in message or "שיניים" in all_text
    
    # Debug logging  
    print(f"DEBUG: message='{message}', all_text='{all_text}', is_dental={is_dental}, has_hmo={has_hmo}, has_tier={has_tier}")
    
    # Override: if we have both hmo+tier for dental, we're sufficient
    if has_hmo and has_tier and is_dental:
        data["missing_fields"] = []
        data["sufficient_context_for_answer"] = True
        data["next_question"] = ""
    elif has_hmo and not has_tier and is_dental:
        data["missing_fields"] = ["tier"]
        data["sufficient_context_for_answer"] = False
    elif not has_hmo and is_dental:
        data["missing_fields"] = ["hmo", "tier"] if not has_tier else ["hmo"]
        data["sufficient_context_for_answer"] = False
    
    return data



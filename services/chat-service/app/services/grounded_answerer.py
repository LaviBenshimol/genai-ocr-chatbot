"""
Stage 2: Grounded Answerer
Generates human-like answers based on KB context and user information.
"""
import os
import json
from typing import Dict, List, Any
from openai import AzureOpenAI


def _client() -> AzureOpenAI:
    return AzureOpenAI(
        azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
        api_key=os.environ.get("AZURE_OPENAI_API_KEY", ""),
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21"),
    )


def generate_grounded_answer(
    user_question: str,
    user_profile: Dict[str, Any],
    kb_context: str,
    conversation_history: List[Dict[str, str]],
    language: str,
    max_tokens: int = 1000
) -> Dict[str, Any]:
    """
    Generate a grounded answer based on KB context.
    Only answers questions that can be answered from the provided context.
    """
    
    # Build system prompt based on language
    if language == "he":
        system_prompt = """
אתה עוזר מידע מקצועי לביטוח בריאות בישראל.

התפקיד שלך:
1. לענות רקותן על שאלות ביטוח בריאות בהסתמך על המידע שסופק
2. להיות ידידותי, מקצועי ועוזר  
3. לכתוב בעברית ברורה ופשוטה
4. לסרב בנימוס לשאלות שאינן קשורות לביטוח בריאות
5. אם המידע לא מספיק, לבקש פרטים נוספים

כללים חשובים:
- ענה רקותן על בסיס "מידע השירותים" שמופיע למטה
- אם אין מידע במסמכים, אמר שאין לך מידע על הנושא
- אל תמציא מידע או תנחש
- כלול ציטוטים קצרים בסוגריים [מקור: קובץ/שירות]
- הוסף בסוף: "המידע כללי ואינו מהווה ייעוץ רפואי"
- אם המשתמש שואל על דברים שלא קשורים לביטוח בריאות, אמר: "אני עוזר רק בשאלות ביטוח בריאות"
"""
    else:
        system_prompt = """
You are a professional Israeli health insurance information assistant.

Your role:
1. Answer ONLY health insurance questions based on the provided information
2. Be friendly, professional and helpful
3. Write in clear, simple English
4. Politely refuse questions unrelated to health insurance  
5. If information is insufficient, ask for more details

Important rules:
- Answer ONLY based on "Service Information" provided below
- If no information in documents, say you don't have information on that topic
- Don't invent information or guess
- Include short citations in brackets [source: file/service]
- Add at end: "This information is general and does not constitute medical advice"
- If user asks about non-health-insurance topics, say: "I only help with health insurance questions"
"""

    # Build user prompt with context
    user_prompt = f"""
שאלת המשתמש: {user_question}

פרופיל המשתמש:
- קופת חולים: {user_profile.get('hmo', 'לא צוין')}
- מסלול: {user_profile.get('tier', 'לא צוין')}

מידע השירותים:
{kb_context}

היסטוריית השיחה האחרונה:
{json.dumps(conversation_history[-4:], ensure_ascii=False) if conversation_history else 'אין'}

אנא ענה על השאלה בהתבסס על המידע שסופק. אם המידע לא מספיק, בקש פרטים נוספים.
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    client = _client()
    response = client.chat.completions.create(
        model=os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
        messages=messages,
        temperature=0.2,  # Low temperature for consistent, factual responses
        max_tokens=max_tokens
    )
    
    answer = response.choices[0].message.content or ""
    
    return {
        "answer": answer,
        "token_usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
    }


def format_kb_context_for_llm(snippets: List[Dict[str, Any]]) -> str:
    """Format KB snippets into readable context for the LLM."""
    if not snippets:
        return "אין מידע זמין במערכת."
    
    formatted_sections = []
    current_category = None
    
    for snippet in snippets:
        category = snippet.get('category', '')
        service = snippet.get('service', '')
        fund = snippet.get('fund', '')
        plan = snippet.get('plan', '')
        text = snippet.get('text', '')
        source_file = snippet.get('source_file', '')
        
        # Group by category
        if category != current_category:
            if current_category:
                formatted_sections.append("")  # Add spacing between categories
            formatted_sections.append(f"## {category}")
            current_category = category
        
        # Add service info
        formatted_sections.append(f"**{service}** - {fund} {plan}:")
        formatted_sections.append(f"  {text} [מקור: {source_file}]")
    
    return "\n".join(formatted_sections)


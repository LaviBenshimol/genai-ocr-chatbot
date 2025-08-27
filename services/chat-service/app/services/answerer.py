"""
Answerer: grounded answer generation using Azure OpenAI (GPT-4o).
Low temperature, capped output tokens, language mirrored to user.
"""
import os
from typing import Dict, Any, List
from openai import AzureOpenAI


def _client() -> AzureOpenAI:
    return AzureOpenAI(
        azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
        api_key=os.environ.get("AZURE_OPENAI_API_KEY", ""),
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21"),
    )


def _build_system_prompt(language: str) -> str:
    if language == "en":
        return (
            "You are a careful assistant. Answer ONLY using the Service Information provided.\n"
            "If information is insufficient, say what is missing and ask ONE targeted question that includes the missing values.\n"
            "Do not invent offers. Keep temperature low. Include short inline citations like [source: file/section]."
        )
    # default Hebrew
    return (
        "אתה מסייע זהיר. השב אך ורק על בסיס 'מידע השירות' שסופק.\n"
        "אם המידע חלקי, ציין מה חסר ושאל שאלה אחת ממוקדת הכוללת את הערכים החסרים.\n"
        "אל תמציא הטבות. טמפרטורה נמוכה. הוסף סימוכין קצרים כמו [source: קובץ/סעיף]."
    )


def generate_answer(
    message: str,
    profile: Dict[str, Any],
    missing_fields: List[str],
    snippets: List[Dict[str, Any]],
    citations: List[Dict[str, Any]],
    language: str,
    max_tokens: int = 1000,
) -> Dict[str, Any]:
    system_prompt = _build_system_prompt(language)

    known_fields = {k: v for k, v in profile.items() if v}
    svc_info_lines: List[str] = []
    for s in snippets:
        tag = f"{s.get('source_file','')}/{s.get('service','')}/{s.get('fund','')}/{s.get('plan','')}"
        svc_info_lines.append(f"[{tag}] {s.get('text','')}")
    service_information = "\n".join(svc_info_lines)

    if language == "en":
        user_prompt = (
            f"Known user details: {known_fields}\n"
            f"Missing details: {missing_fields}\n"
            f"Service Information:\n{service_information}\n\n"
            f"Question: {message}\n"
            f"Answer in English."
        )
        disclaimer = "Information is general and not medical advice."
    else:
        user_prompt = (
            f"פרטים ידועים: {known_fields}\n"
            f"פרטים חסרים: {missing_fields}\n"
            f"מידע השירות:\n{service_information}\n\n"
            f"שאלה: {message}\n"
            f"השב בעברית."
        )
        disclaimer = "המידע כללי ואינו מהווה ייעוץ רפואי."

    client = _client()
    resp = client.chat.completions.create(
        model=os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
        max_tokens=max_tokens,
    )
    content = resp.choices[0].message.content or ""
    usage = resp.usage

    return {
        "answer": content,
        "citations": citations,
        "token_usage": {
            "prompt_tokens": getattr(usage, "prompt_tokens", 0),
            "completion_tokens": getattr(usage, "completion_tokens", 0),
            "total_tokens": getattr(usage, "total_tokens", 0),
        },
        "disclaimer": disclaimer,
    }



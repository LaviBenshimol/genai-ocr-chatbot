#!/usr/bin/env python3
"""
Simple console tests for Chat Service (Phase 2), similar to health-form test.
"""
import requests
import json
import time

SERVICE_URL = "http://localhost:5000"


def test_health():
    r = requests.get(f"{SERVICE_URL}/health", timeout=5)
    print("[health]", r.status_code, r.text)


def chat(payload):
    r = requests.post(f"{SERVICE_URL}/v1/chat", json=payload, timeout=60)
    print("[chat]", r.status_code)
    try:
        data = r.json()
        print(json.dumps(data, ensure_ascii=False, indent=2))
    except Exception:
        print(r.text)


def scenario():
    user_profile = {}
    conversation_history = []
    
    # 1) First question (insufficient)
    print("\n=== Turn 1: Initial dental question ===")
    payload = {
        "message": "מה ההטבות לטיפולי שיניים?",
        "language": "he",
        "user_profile": user_profile.copy(),
        "conversation_history": conversation_history.copy()
    }
    response = requests.post(f"{SERVICE_URL}/v1/chat", json=payload, timeout=60)
    data = response.json()
    print(f"[chat] {response.status_code}")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    
    # Update conversation history
    conversation_history.append({"role": "user", "content": payload["message"]})
    if data.get("next_question"):
        conversation_history.append({"role": "assistant", "content": data["next_question"]})
    user_profile.update(data.get("updated_profile", {}))
    time.sleep(1)

    # 2) Provide HMO (still insufficient)
    print("\n=== Turn 2: Provide HMO ===")
    payload = {
        "message": "אני במכבי",
        "language": "he", 
        "user_profile": user_profile.copy(),
        "conversation_history": conversation_history.copy()
    }
    response = requests.post(f"{SERVICE_URL}/v1/chat", json=payload, timeout=60)
    data = response.json()
    print(f"[chat] {response.status_code}")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    
    # Update conversation history
    conversation_history.append({"role": "user", "content": payload["message"]})
    if data.get("next_question"):
        conversation_history.append({"role": "assistant", "content": data["next_question"]})
    user_profile.update(data.get("updated_profile", {}))
    time.sleep(1)

    # 3) Provide tier (sufficient → answer)
    print("\n=== Turn 3: Provide tier - should get ANSWER ===")
    payload = {
        "message": "זהב",
        "language": "he",
        "user_profile": user_profile.copy(),
        "conversation_history": conversation_history.copy()
    }
    response = requests.post(f"{SERVICE_URL}/v1/chat", json=payload, timeout=60)
    data = response.json()
    print(f"[chat] {response.status_code}")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    
    # Check if we got an answer
    if data.get("action") == "answer":
        print("\n✅ SUCCESS: Got answer!")
        print(f"Answer: {data.get('answer', 'N/A')}")
        print(f"Citations: {len(data.get('citations', []))}")
    else:
        print(f"\n❌ FAILED: Still collecting, action={data.get('action')}")
        print(f"Missing fields: {data.get('missing_fields')}")


if __name__ == "__main__":
    test_health()
    scenario()



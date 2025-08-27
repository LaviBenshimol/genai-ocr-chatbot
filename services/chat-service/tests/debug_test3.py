#!/usr/bin/env python3
import requests
import json

def test_call_3():
    payload = {
        "message": "זהב",
        "language": "he",
        "user_profile": {"hmo": "מכבי"},
        "conversation_history": [
            {"role": "user", "content": "מה ההטבות לטיפולי שיניים?"},
            {"role": "assistant", "content": "באיזו קופת חולים אתה חבר?"},
            {"role": "user", "content": "אני במכבי"},
            {"role": "assistant", "content": "מה המסלול שלך?"}
        ]
    }
    
    print("Testing problematic call 3...")
    response = requests.post("http://localhost:8000/v1/chat", json=payload, timeout=30)
    
    if response.status_code == 200:
        data = response.json()
        print(f"Action: {data.get('action')}")
        print(f"Missing: {data.get('missing_fields')}")
        print(f"Sufficient: {data.get('sufficient_context')}")
        print(f"Updated Profile: {data.get('updated_profile')}")
    else:
        print(f"ERROR: {response.status_code} - {response.text}")

if __name__ == "__main__":
    test_call_3()

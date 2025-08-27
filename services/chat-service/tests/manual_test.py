#!/usr/bin/env python3
"""
Manual test for debugging chat service step by step
"""
import requests
import json

SERVICE_URL = "http://localhost:8000"

def test_single_call(message, profile, history, description):
    print(f"\n{'='*60}")
    print(f"TEST: {description}")
    print(f"{'='*60}")
    
    payload = {
        "message": message,
        "language": "he",
        "user_profile": profile,
        "conversation_history": history
    }
    
    print("REQUEST:")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    
    try:
        response = requests.post(f"{SERVICE_URL}/v1/chat", json=payload, timeout=30)
        print(f"\nRESPONSE ({response.status_code}):")
        
        if response.status_code == 200:
            data = response.json()
            print(json.dumps(data, ensure_ascii=False, indent=2))
            
            # Extract key info
            print(f"\nKEY INFO:")
            print(f"  Action: {data.get('action')}")
            print(f"  Intent: {data.get('intent')}")
            print(f"  Sufficient: {data.get('sufficient_context')}")
            print(f"  Missing: {data.get('missing_fields')}")
            print(f"  Updated Profile: {data.get('updated_profile')}")
            print(f"  KB Context: {data.get('context_metrics', {}).get('kb_context_chars', 0)} chars")
            
            return data
        else:
            print(response.text)
            return None
            
    except Exception as e:
        print(f"ERROR: {e}")
        return None

def main():
    print("🧪 Manual Chat Service Test")
    
    # Test 1: Initial question
    test_single_call(
        message="מה ההטבות לטיפולי שיניים?",
        profile={},
        history=[],
        description="Initial dental question - should ask for HMO+tier"
    )
    
    # Test 2: Provide HMO
    test_single_call(
        message="אני במכבי",
        profile={},
        history=[
            {"role": "user", "content": "מה ההטבות לטיפולי שיניים?"},
            {"role": "assistant", "content": "באיזו קופת חולים אתה חבר?"}
        ],
        description="Provide HMO - should ask for tier"
    )
    
    # Test 3: Provide tier
    test_single_call(
        message="זהב",
        profile={"hmo": "מכבי"},
        history=[
            {"role": "user", "content": "מה ההטבות לטיפולי שיניים?"},
            {"role": "assistant", "content": "באיזו קופת חולים אתה חבר?"},
            {"role": "user", "content": "אני במכבי"},
            {"role": "assistant", "content": "מה המסלול שלך?"}
        ],
        description="Provide tier - should ANSWER with KB content"
    )
    
    # Test 4: Both at once
    test_single_call(
        message="מה ההטבות לטיפולי שיניים במכבי זהב?",
        profile={},
        history=[],
        description="Both HMO+tier in message - should ANSWER immediately"
    )

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from services.chat_health_kb import ChatHealthKB

def test_kb():
    kb_dir = os.path.join(os.getcwd(), 'data', 'phase2_data')
    print(f"KB Directory: {kb_dir}")
    
    kb = ChatHealthKB(kb_dir)
    print(f"Categories loaded: {len(kb.by_category)}")
    
    # Test the exact retrieval call from the service
    result = kb.retrieve(
        message="מה ההטבות לטיפולי שיניים?",
        profile={"hmo": "מכבי", "tier": "זהב"},
        language="he",
        max_chars=3500
    )
    
    print(f"Snippets: {len(result['snippets'])}")
    print(f"Context chars: {result['context_chars']}")
    print(f"Citations: {len(result['citations'])}")
    
    if result['snippets']:
        print("First snippet:")
        print(result['snippets'][0])
    else:
        print("No snippets returned!")

if __name__ == "__main__":
    test_kb()


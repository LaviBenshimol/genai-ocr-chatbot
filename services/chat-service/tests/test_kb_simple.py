#!/usr/bin/env python3
"""
Simple KB test - just verify it loads and retrieves
"""
import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from services.chat_health_kb import ChatHealthKB

def main():
    # Find KB directory
    kb_dir = os.path.join(os.getcwd(), 'data', 'phase2_data')
    print(f"KB Directory: {kb_dir}")
    print(f"Exists: {os.path.exists(kb_dir)}")
    
    if not os.path.exists(kb_dir):
        print("❌ KB directory not found!")
        return
    
    # List files
    files = os.listdir(kb_dir)
    html_files = [f for f in files if f.endswith('.html')]
    print(f"HTML files: {html_files}")
    
    # Load KB
    kb = ChatHealthKB(kb_dir)
    print(f"Categories loaded: {len(kb.by_category)}")
    
    # Test retrieval
    result = kb.retrieve(
        message="מה ההטבות לטיפולי שיניים?",
        profile={"hmo": "מכבי", "tier": "זהב"},
        language="he"
    )
    
    print(f"Retrieved: {len(result['snippets'])} snippets")
    print(f"Context chars: {result['context_chars']}")
    
    if result['snippets']:
        snippet = result['snippets'][0]
        print(f"First snippet: {snippet['category']} - {snippet['service']} - {snippet['fund']} - {snippet['plan']}")

if __name__ == "__main__":
    main()

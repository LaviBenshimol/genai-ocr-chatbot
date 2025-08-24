"""
Test script for Knowledge Service
Run this to test the knowledge service functionality
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Set up logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from src.knowledge_service import KnowledgeService

def test_knowledge_service():
    """Test the knowledge service"""
    
    # Initialize knowledge service
    knowledge_base_dir = project_root / "data" / "phase2_data"
    ks = KnowledgeService(knowledge_base_dir)
    
    print("=== Testing Knowledge Service ===")
    
    # Test 1: General question without user context
    print("\n1. Testing general question (no user context):")
    question1 = "מה ההטבות על דיקור סיני?"
    result1 = ks.get_service_info(question1)
    print(f"Question: {question1}")
    print(f"Result length: {len(result1)} characters")
    print(f"First 200 chars: {result1[:200]}...")
    
    # Test 2: Question with user context
    print("\n2. Testing personalized question (with user context):")
    user_context = {
        "hmo": "כללית",
        "tier": "זהב",
        "name": "יוסי כהן"
    }
    question2 = "כמה עולה טיפול דיקור סיני?"
    result2 = ks.get_service_info(question2, user_context)
    print(f"Question: {question2}")
    print(f"User Context: {user_context}")
    print(f"Result length: {len(result2)} characters")
    print(f"First 300 chars: {result2[:300]}...")
    
    # Test 3: Different service type
    print("\n3. Testing dental service:")
    question3 = "מה עולה טיפול שיניים?"
    result3 = ks.get_service_info(question3, user_context)
    print(f"Question: {question3}")
    print(f"Result length: {len(result3)} characters")
    print(f"First 200 chars: {result3[:200]}...")

if __name__ == "__main__":
    test_knowledge_service()
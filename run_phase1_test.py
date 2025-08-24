#!/usr/bin/env python3
"""
Quick Phase 1 Test Runner
Compact script to test Azure integration with PDF samples
"""
import sys
from pathlib import Path

# Add paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "services"))
sys.path.insert(0, str(project_root / "tests"))

# Run the test
if __name__ == "__main__":
    print("🧪 Running Phase 1 Azure Integration Test")
    print("=" * 50)
    
    # Check if .env exists
    env_file = project_root / ".env"
    if not env_file.exists():
        print("❌ .env file not found!")
        print("📋 Please create .env file with your Azure credentials")
        print("💡 Copy .env.example to .env and fill in your credentials")
        sys.exit(1)
    
    print(f"✅ Configuration file found: {env_file}")
    
    # Show logs directory
    logs_dir = project_root / "logs"
    print(f"📁 Logs will be stored in: {logs_dir}")
    
    # Import and run test
    try:
        import asyncio
        from test_phase1_azure import main
        
        print("🚀 Starting Azure integration test...")
        asyncio.run(main())
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure to install requirements: pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
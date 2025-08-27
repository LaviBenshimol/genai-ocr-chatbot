#!/usr/bin/env python3
"""
Chat Service V2 Runner
Enhanced chat service with improved KB integration and fallback logic
"""
import os
import sys
import logging

# Add parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from app.main import create_app

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    app = create_app()
    
    logger.info("Starting Chat Service V2...")
    logger.info("Enhanced features:")
    logger.info("- Uses existing ChromaDB data")
    logger.info("- Improved fallback logic") 
    logger.info("- Polite information collection")
    logger.info("- Better service scope detection")
    
    port = int(os.environ.get("CHAT_SERVICE_V2_PORT", 5002))
    
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        threaded=True
    )

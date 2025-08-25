"""
Application Settings
Centralized configuration management with environment variable loading
"""
import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=False)

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
UPLOADS_DIR = DATA_DIR / "uploads"
SERVICES_DIR = PROJECT_ROOT / "services"

# Ensure directories exist
LOGS_DIR.mkdir(exist_ok=True)
UPLOADS_DIR.mkdir(exist_ok=True)

# User storage
USERS_JSON_PATH = DATA_DIR / "users.json"

# Knowledge base
KNOWLEDGE_BASE_DIR = DATA_DIR / "phase2_data"
PHASE1_DATA_DIR = DATA_DIR / "phase1_data"

# MCP Server settings
MCP_PHASE1_PORT = int(os.getenv("MCP_PHASE1_PORT", "3001"))
MCP_PHASE2_PORT = int(os.getenv("MCP_PHASE2_PORT", "3002"))

# Azure OpenAI settings
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-11-20")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "")

# Azure Document Intelligence settings
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", "")
AZURE_DOCUMENT_INTELLIGENCE_KEY = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY", "")
AZURE_DOCUMENT_INTELLIGENCE_API_VERSION = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_API_VERSION", "2023-07-31")
AZURE_DOC_INTEL_MODEL = os.getenv("AZURE_DOC_INTEL_MODEL", "prebuilt-document")

# Application settings
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# File upload limits (updated based on our requirements)
MAX_FILE_SIZE_MB = 5  # 5MB limit
MAX_PDF_PAGES = 2     # 2 pages max
ALLOWED_EXTENSIONS = {".pdf"}  # PDF only for production

# Validation settings
def validate_configuration() -> dict:
    """Validate that required configuration is available"""
    errors = []
    warnings = []
    
    # Check Azure credentials if not in demo mode
    if not DEMO_MODE:
        if not AZURE_OPENAI_ENDPOINT:
            errors.append("AZURE_OPENAI_ENDPOINT not configured")
        if not AZURE_OPENAI_API_KEY:
            errors.append("AZURE_OPENAI_API_KEY not configured")
        if not AZURE_OPENAI_DEPLOYMENT_NAME:
            errors.append("AZURE_OPENAI_DEPLOYMENT_NAME not configured")
        if not AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT:
            errors.append("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT not configured")
        if not AZURE_DOCUMENT_INTELLIGENCE_KEY:
            errors.append("AZURE_DOCUMENT_INTELLIGENCE_KEY not configured")
    
    # Check directories
    required_dirs = [PROJECT_ROOT, DATA_DIR, PHASE1_DATA_DIR, KNOWLEDGE_BASE_DIR]
    for directory in required_dirs:
        if not directory.exists():
            warnings.append(f"Directory not found: {directory}")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "demo_mode": DEMO_MODE
    }
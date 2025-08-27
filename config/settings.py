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
AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME", "text-embedding-ada-002")

# Azure Document Intelligence settings
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", "")
AZURE_DOCUMENT_INTELLIGENCE_KEY = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY", "")
AZURE_DOCUMENT_INTELLIGENCE_API_VERSION = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_API_VERSION", "2023-07-31")
AZURE_DOC_INTEL_MODEL = os.getenv("AZURE_DOC_INTEL_MODEL", "prebuilt-document")

# LLM Confidence Analysis settings
# Temperature: Controls randomness in confidence scoring (0.0 = deterministic, 1.0 = random)
# Low values (0.1-0.3) recommended for consistent confidence scoring
LLM_CONFIDENCE_TEMPERATURE = float(os.getenv("LLM_CONFIDENCE_TEMPERATURE", "0.1"))

# Top-p: Controls nucleus sampling diversity (0.1 = very focused, 1.0 = full vocabulary)
# Moderate values (0.9-0.95) allow variation in reasoning explanations while maintaining focus
LLM_CONFIDENCE_TOP_P = float(os.getenv("LLM_CONFIDENCE_TOP_P", "0.95"))

# Max tokens: Maximum tokens for confidence analysis response
# Should accommodate detailed field analysis + reasoning (1500-2500 recommended)
LLM_CONFIDENCE_MAX_TOKENS = int(os.getenv("LLM_CONFIDENCE_MAX_TOKENS", "2000"))

# Presence penalty: Reduces likelihood of repeating topics (-2.0 to 2.0)
# 0.0 recommended for field coverage - we want all fields analyzed
LLM_CONFIDENCE_PRESENCE_PENALTY = float(os.getenv("LLM_CONFIDENCE_PRESENCE_PENALTY", "0.0"))

# Frequency penalty: Reduces likelihood of repeating tokens (-2.0 to 2.0) 
# 0.0 recommended to allow consistent validation patterns across fields
LLM_CONFIDENCE_FREQUENCY_PENALTY = float(os.getenv("LLM_CONFIDENCE_FREQUENCY_PENALTY", "0.0"))

# Seed: For reproducible results (optional, set to None for random)
# Use integer for deterministic confidence scoring, None for varied analysis
LLM_CONFIDENCE_SEED = os.getenv("LLM_CONFIDENCE_SEED")
if LLM_CONFIDENCE_SEED and LLM_CONFIDENCE_SEED.lower() != "none":
    LLM_CONFIDENCE_SEED = int(LLM_CONFIDENCE_SEED)
else:
    LLM_CONFIDENCE_SEED = None

# Timeout: Request timeout in seconds for confidence analysis
LLM_CONFIDENCE_TIMEOUT = int(os.getenv("LLM_CONFIDENCE_TIMEOUT", "60"))

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
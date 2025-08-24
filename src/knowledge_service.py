"""
Knowledge Service for Medical Services Information
Two-stage implementation: Stage 1 (simple text) -> Stage 2 (structured parsing)
"""
import logging
from pathlib import Path
from typing import Dict, Optional, List
import re
from bs4 import BeautifulSoup

# Set up logging
logger = logging.getLogger(__name__)

class KnowledgeService:
    """
    Two-stage knowledge service for medical services information
    Stage 1: Simple HTML text extraction
    Stage 2: Structured parsing with context-aware responses (future)
    """
    
    def __init__(self, knowledge_base_dir: Path):
        self.knowledge_base_dir = Path(knowledge_base_dir)
        self.stage = 1  # Current implementation stage
        
        # Available service files
        self.service_files = {
            "alternative_medicine": "alternative_services.html",
            "dental": "dentel_services.html", 
            "optometry": "optometry_services.html",
            "pregnancy": "pragrency_services.html",
            "communication_clinic": "communication_clinic_services.html",
            "workshops": "workshops_services.html"
        }
        
        logger.info(f"Knowledge service initialized - Stage {self.stage}")

    def get_service_info(self, 
                        question: str, 
                        user_context: Optional[Dict] = None,
                        service_type: Optional[str] = None) -> str:
        """
        Main API for getting service information
        Args:
            question: User's question
            user_context: User profile from OCR (HMO, tier, etc.) - can be None
            service_type: Specific service type or None for auto-detection
        Returns:
            Service information text for Azure OpenAI processing
        """
        logger.info(f"Getting service info for question: {question[:50]}...")
        
        if user_context:
            logger.info(f"User context available: HMO={user_context.get('hmo', 'unknown')}")
            return self._get_personalized_info(question, user_context, service_type)
        else:
            logger.info("No user context - providing general information")
            return self._get_general_info(question, service_type)
    
    def _get_personalized_info(self, question: str, user_context: Dict, service_type: Optional[str]) -> str:
        """Get personalized information based on user's HMO and tier"""

        # Extract user details
        hmo = user_context.get('hmo', '').strip()
        tier = user_context.get('tier', '').strip()
        
        # Detect service type if not provided
        if not service_type:
            service_type = self._detect_service_type(question)
        
        # Get relevant HTML content
        html_content = self._load_service_html(service_type)
        if not html_content:
            return "מצטער, לא הצלחתי לטעון את המידע על השירות המבוקש."
        
        # Stage 1: Simple text extraction with user context hint
        service_text = self._extract_text_from_html(html_content)
        
        # Add user context to the response for Azure OpenAI
        context_prompt = f"""
        User Information:
        - HMO: {hmo}
        - Membership Tier: {tier}
        - Question: {question}
        
        Service Information:
        {service_text}
        
        Please provide a personalized answer based on the user's HMO and membership tier.
        """
        
        return context_prompt
    
    def _get_general_info(self, question: str, service_type: Optional[str]) -> str:
        """Get general information without user context"""

        # Detect service type if not provided  
        if not service_type:
            service_type = self._detect_service_type(question)
            
        # Get relevant HTML content
        html_content = self._load_service_html(service_type)
        if not html_content:
            return "מצטער, לא הצלחתי לטעון את המידע על השירות המבוקש."
        
        # Stage 1: Simple text extraction
        service_text = self._extract_text_from_html(html_content)
        
        # Format for Azure OpenAI without user context
        general_prompt = f"""
        Question: {question}
        
        Service Information:
        {service_text}
        
        Please provide a general overview of the available services from all health funds.
        """
        
        return general_prompt
    
    def _detect_service_type(self, question: str) -> str:
        """Detect service type from question keywords"""

        question_lower = question.lower()
        
        # Hebrew and English keywords for each service
        keywords = {
            "alternative_medicine": ["דיקור", "שיאצו", "רפלקסולוגיה", "נטורופתיה", "הומאופתיה", "כירופרקטיקה",
                                   "acupuncture", "shiatsu", "reflexology", "naturopathy", "homeopathy", "chiropractic", "alternative"],
            "dental": ["שיניים", "רופא שיניים", "סתימה", "כתר", "השתלה", "יישור",
                      "dental", "dentist", "tooth", "teeth", "filling", "crown", "implant", "orthodontic"],
            "optometry": ["עיניים", "משקפיים", "בדיקת עיניים", "אופטומטריה",
                         "eyes", "glasses", "eye exam", "optometry", "vision"],
            "pregnancy": ["הריון", "לידה", "הריונות", "יולדת", "גינקולוגיה",
                         "pregnancy", "birth", "maternity", "gynecology", "prenatal"],
            "communication_clinic": ["תקשורת", "קלינקה", "שפה", "דיבור",
                                   "communication", "speech", "language", "therapy"],
            "workshops": ["סדנה", "קורס", "הרצאה", "סדנאות",
                         "workshop", "course", "lecture", "seminar"]
        }
        
        # Count matches for each service type
        service_scores = {}
        for service, service_keywords in keywords.items():
            score = sum(1 for keyword in service_keywords if keyword in question_lower)
            if score > 0:
                service_scores[service] = score
        
        # Return service with highest score, default to alternative_medicine
        detected_service = max(service_scores.items(), key=lambda x: x[1])[0] if service_scores else "alternative_medicine"
        
        logger.info(f"Detected service type: {detected_service} from question: {question[:50]}...")
        return detected_service
    
    def _load_service_html(self, service_type: str) -> Optional[str]:
        """Load HTML content for a specific service type"""

        filename = self.service_files.get(service_type)
        if not filename:
            logger.error(f"Unknown service type: {service_type}")
            return None
        
        file_path = self.knowledge_base_dir / filename
        
        if not file_path.exists():
            logger.error(f"Service file not found: {file_path}")
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                logger.info(f"Loaded HTML file: {filename} ({len(content)} characters)")
                return content
        except Exception as e:
            logger.error(f"Error loading service file {filename}: {e}")
            return None
    
    def _extract_text_from_html(self, html_content: str) -> str:
        """Stage 1: Simple text extraction from HTML"""

        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()
            
            # Get text and clean it up
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            logger.info(f"Extracted text: {len(text)} characters")
            return text
            
        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            return "שגיאה בעיבוד המידע"
    
    # Future Stage 2 methods (placeholder for now)
    def _parse_html_table(self, html_content: str) -> Dict:
        """Stage 2: Parse HTML tables into structured data (future implementation)"""
        pass
    
    def _get_hmo_specific_info(self, service_data: Dict, hmo: str, tier: str) -> Dict:
        """Stage 2: Extract specific HMO and tier information (future implementation)"""
        pass


# Utility function for easy access
def get_knowledge_service() -> KnowledgeService:
    """Get knowledge service instance"""
    from config.settings import KNOWLEDGE_BASE_DIR
    return KnowledgeService(KNOWLEDGE_BASE_DIR)
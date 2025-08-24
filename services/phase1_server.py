"""
Phase 1 MCP Server: OCR Field Extraction Service
Uses Azure Document Intelligence + Azure OpenAI for Israeli National Insurance forms
"""
import asyncio
from typing import Dict, Any
from datetime import datetime

# MCP imports (we'll add these when implementing MCP protocol)
# from mcp.server import Server
# from mcp.types import Tool

# Centralized imports
from shared_utils import (
    get_document_intelligence_client, 
    get_openai_client, 
    IsraeliValidators,
    MarkItDownProcessor
)
from src.logger_config import get_logger

logger = get_logger('phase1_server')

class Phase1OCRService:
    """
    Phase 1 OCR Service for Israeli National Insurance forms
    Handles document analysis and field extraction
    """
    
    def __init__(self):
        """Initialize the OCR service with Azure clients"""
        self.doc_intel_client = None
        self.openai_client = None
        self.validators = IsraeliValidators()
        
        logger.info("Phase 1 OCR Service initialized")
        print("🔍 DEBUG - Phase 1 OCR Service starting...")
    
    async def initialize_clients(self):
        """Initialize Azure clients with fallback (lazy loading)"""
        try:
            if not self.doc_intel_client:
                try:
                    self.doc_intel_client = get_document_intelligence_client()
                    print("🔍 DEBUG - Document Intelligence client initialized")
                except Exception as e:
                    logger.warning(f"Azure Document Intelligence failed, using MarkItDown fallback: {e}")
                    print("🔍 DEBUG - Falling back to MarkItDown processor")
                    self.doc_intel_client = MarkItDownProcessor()
            
            if not self.openai_client:
                self.openai_client = get_openai_client()
                print("🔍 DEBUG - Azure OpenAI client initialized")
                
            return True
        except Exception as e:
            logger.error(f"Failed to initialize clients: {e}")
            print(f"🔍 DEBUG - Client initialization FAILED: {e}")
            return False
    
    async def process_document(self, file_bytes: bytes, filename: str, language: str = "Auto-detect") -> Dict[str, Any]:
        """
        Main document processing pipeline
        
        Args:
            file_bytes: PDF file content
            filename: Original filename
            language: Document language preference
            
        Returns:
            Complete processing result with extracted fields and validation
        """
        logger.info(f"Starting document processing pipeline for: {filename}")
        print(f"🔍 DEBUG - Processing pipeline started: {filename}, language={language}")
        
        processing_result = {
            "filename": filename,
            "processing_timestamp": datetime.now().isoformat(),
            "language": language,
            "success": False,
            "stages": {
                "client_initialization": {"success": False},
                "document_analysis": {"success": False},
                "field_extraction": {"success": False},
                "validation": {"success": False}
            },
            "extracted_fields": {},
            "validation_results": {},
            "errors": []
        }
        
        try:
            # Stage 1: Initialize clients
            print("🔍 DEBUG - Stage 1: Initializing Azure clients...")
            client_init_success = await self.initialize_clients()
            processing_result["stages"]["client_initialization"]["success"] = client_init_success
            
            if not client_init_success:
                processing_result["errors"].append("Failed to initialize Azure clients")
                return processing_result
            
            # Stage 2: Document Analysis with Azure Document Intelligence
            print("🔍 DEBUG - Stage 2: Analyzing document with Document Intelligence...")
            doc_analysis = await self.doc_intel_client.analyze_document(file_bytes, filename)
            processing_result["stages"]["document_analysis"]["success"] = True
            processing_result["stages"]["document_analysis"]["data"] = doc_analysis
            
            # Stage 3: Field Extraction with Azure OpenAI
            print("🔍 DEBUG - Stage 3: Extracting fields with Azure OpenAI...")
            field_extraction = await self.openai_client.extract_fields_from_text(
                doc_analysis["full_text"], 
                language
            )
            processing_result["stages"]["field_extraction"]["success"] = field_extraction["extraction_successful"]
            processing_result["extracted_fields"] = field_extraction["extracted_fields"]
            
            if not field_extraction["extraction_successful"]:
                processing_result["errors"].append(f"Field extraction failed: {field_extraction.get('error', 'Unknown error')}")
            
            # Stage 4: Validation
            print("🔍 DEBUG - Stage 4: Validating extracted fields...")
            validation_results = await self.validate_extracted_fields(field_extraction["extracted_fields"])
            processing_result["stages"]["validation"]["success"] = True
            processing_result["validation_results"] = validation_results
            
            # Overall success
            processing_result["success"] = all(
                stage["success"] for stage in processing_result["stages"].values()
            ) and field_extraction["extraction_successful"]
            
            logger.info(f"Document processing completed for {filename}: success={processing_result['success']}")
            print(f"🔍 DEBUG - Processing pipeline completed: success={processing_result['success']}")
            
        except Exception as e:
            logger.error(f"Document processing failed for {filename}: {e}")
            print(f"🔍 DEBUG - Processing pipeline FAILED: {str(e)}")
            processing_result["errors"].append(str(e))
        
        return processing_result
    
    async def validate_extracted_fields(self, extracted_fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate extracted fields using Israeli-specific validation
        
        Args:
            extracted_fields: Fields extracted from the document
            
        Returns:
            Validation results for each field
        """
        print("🔍 DEBUG - Starting field validation...")
        
        validation_results = {
            "overall_valid": True,
            "field_validations": {},
            "validation_timestamp": datetime.now().isoformat()
        }
        
        # Validate Israeli ID
        id_number = extracted_fields.get("idNumber", "")
        if id_number:
            id_validation = self.validators.validate_israeli_id(id_number)
            validation_results["field_validations"]["idNumber"] = id_validation
            if not id_validation["valid"]:
                validation_results["overall_valid"] = False
        
        # Validate phone numbers
        for phone_field in ["landlinePhone", "mobilePhone"]:
            phone = extracted_fields.get(phone_field, "")
            if phone:
                phone_validation = self.validators.validate_israeli_phone(phone)
                validation_results["field_validations"][phone_field] = phone_validation
                if not phone_validation["valid"]:
                    validation_results["overall_valid"] = False
        
        # Validate date fields
        date_fields = ["dateOfBirth", "dateOfInjury", "formFillingDate", "formReceiptDateAtClinic"]
        for date_field in date_fields:
            date_obj = extracted_fields.get(date_field, {})
            if isinstance(date_obj, dict) and any(date_obj.values()):
                date_validation = self._validate_date(date_obj, date_field)
                validation_results["field_validations"][date_field] = date_validation
                if not date_validation["valid"]:
                    validation_results["overall_valid"] = False
        
        print(f"🔍 DEBUG - Validation completed: overall_valid={validation_results['overall_valid']}")
        return validation_results
    
    def _validate_date(self, date_obj: Dict[str, str], field_name: str) -> Dict[str, Any]:
        """Validate a date object"""
        try:
            day = int(date_obj.get("day", 0)) if date_obj.get("day") else 0
            month = int(date_obj.get("month", 0)) if date_obj.get("month") else 0
            year = int(date_obj.get("year", 0)) if date_obj.get("year") else 0
            
            # Basic validation
            if not (1 <= day <= 31):
                return {"valid": False, "error": f"Invalid day: {day}"}
            if not (1 <= month <= 12):
                return {"valid": False, "error": f"Invalid month: {month}"}
            if not (1900 <= year <= 2030):
                return {"valid": False, "error": f"Invalid year: {year}"}
            
            return {"valid": True, "error": None}
            
        except ValueError as e:
            return {"valid": False, "error": f"Date parsing error: {e}"}


# For testing without MCP protocol
async def test_ocr_service():
    """Test function for OCR service"""
    print("🧪 Testing OCR Service...")
    
    service = Phase1OCRService()
    
    # Test with a sample file (you would load actual file bytes here)
    # This is just for testing the service structure
    sample_text = "Test document content"
    sample_bytes = sample_text.encode('utf-8')
    
    result = await service.process_document(sample_bytes, "test.pdf", "Hebrew")
    
    print(f"Test result: {json.dumps(result, indent=2, ensure_ascii=False)}")


if __name__ == "__main__":
    # Run test
    asyncio.run(test_ocr_service())
"""
Shared utilities for MCP servers
Azure clients, validation functions, and common utilities
"""
import asyncio
from typing import Dict, Optional, Any
import json
import re
from datetime import datetime

# Azure imports
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import openai

# Fallback document processing
from markitdown import MarkItDown

# Centralized imports
from config.settings import (
    AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_API_VERSION, AZURE_OPENAI_DEPLOYMENT_NAME,
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT, AZURE_DOCUMENT_INTELLIGENCE_KEY, AZURE_DOCUMENT_INTELLIGENCE_API_VERSION,
    AZURE_DOC_INTEL_MODEL
)
from src.logger_config import get_logger

logger = get_logger('shared_utils')

class MarkItDownProcessor:
    """
    MarkItDown document processor - fallback for Azure Document Intelligence
    Local processing, no API limits
    """
    
    def __init__(self):
        self.markitdown = MarkItDown()
        logger.info("MarkItDown processor initialized (fallback mode)")
        print("🔍 DEBUG - MarkItDown fallback processor initialized")
    
    async def analyze_document(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Analyze document using MarkItDown (local processing)
        """
        logger.info(f"Processing document with MarkItDown: {filename}")
        print(f"🔍 DEBUG - MarkItDown processing: {filename}")
        
        try:
            # MarkItDown expects file path, so save temporarily  
            from config.settings import UPLOADS_DIR
            temp_file = UPLOADS_DIR / f"temp_{filename}"
            temp_file.parent.mkdir(exist_ok=True)
            temp_file.write_bytes(file_bytes)
            
            # Convert to markdown
            result = self.markitdown.convert(str(temp_file))
            extracted_text = result.text_content
            
            # Clean up temp file
            temp_file.unlink()
            
            # Format result similar to Azure Document Intelligence
            analysis_result = {
                "filename": filename,
                "full_text": extracted_text,
                "text_length": len(extracted_text),
                "pages": [{"page_number": 1, "text_lines": extracted_text.count('\n')}],
                "page_count": 1,
                "tables": [],
                "table_count": 0,
                "key_value_pairs": [],
                "kv_pair_count": 0,
                "analysis_timestamp": datetime.now().isoformat(),
                "model_used": "markitdown-fallback"
            }
            
            logger.info(f"MarkItDown extracted {len(extracted_text)} characters")
            print(f"🔍 DEBUG - MarkItDown extraction: {len(extracted_text)} chars")
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"MarkItDown processing failed for {filename}: {e}")
            print(f"🔍 DEBUG - MarkItDown FAILED: {str(e)}")
            raise

class AzureDocumentIntelligence:
    """
    Azure Document Intelligence client for OCR processing
    Handles PDF document analysis and text extraction
    """
    
    def __init__(self):
        # Get configuration from centralized settings
        self.endpoint = AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT
        self.key = AZURE_DOCUMENT_INTELLIGENCE_KEY
        self.api_version = AZURE_DOCUMENT_INTELLIGENCE_API_VERSION
        self.model_id = AZURE_DOC_INTEL_MODEL
        
        # Validate configuration
        if not self.endpoint or not self.key:
            raise ValueError("Azure Document Intelligence credentials not found in environment variables")
        
        # Initialize client
        self.client = DocumentAnalysisClient(
            endpoint=self.endpoint,
            credential=AzureKeyCredential(self.key)
        )
        
        logger.info(f"Azure Document Intelligence initialized with model: {self.model_id}")
        print(f"🔍 DEBUG - Document Intelligence initialized: endpoint={self.endpoint[:50]}..., model={self.model_id}")
    
    async def analyze_document(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Analyze document using Azure Document Intelligence
        
        Args:
            file_bytes: PDF file content as bytes
            filename: Original filename for logging
            
        Returns:
            Dict with extracted text and metadata
        """
        logger.info(f"Starting document analysis for: {filename}")
        print(f"🔍 DEBUG - Analyzing document: {filename} with model {self.model_id}")
        
        try:
            # Start document analysis
            poller = self.client.begin_analyze_document(
                model_id=self.model_id,
                document=file_bytes
            )
            
            print(f"🔍 DEBUG - Document analysis started, waiting for results...")
            
            # Get results
            result = poller.result()
            
            logger.info(f"Document analysis completed for: {filename}")
            print(f"🔍 DEBUG - Analysis completed, processing results...")
            
            # Extract information
            analysis_result = self._process_analysis_result(result, filename)
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Document analysis failed for {filename}: {e}")
            print(f"🔍 DEBUG - Document analysis FAILED: {str(e)}")
            raise
    
    def _process_analysis_result(self, result, filename: str) -> Dict[str, Any]:
        """Process Document Intelligence analysis result"""
        print(f"🔍 DEBUG - Processing analysis result for {filename}")
        
        # Extract all text content
        full_text = result.content if result.content else ""
        
        # Extract pages information
        pages_info = []
        for page in result.pages:
            page_info = {
                "page_number": page.page_number,
                "width": page.width,
                "height": page.height,
                "unit": page.unit,
                "text_lines": len(page.lines) if page.lines else 0
            }
            pages_info.append(page_info)
        
        # Extract tables if any
        tables_info = []
        if result.tables:
            for table_idx, table in enumerate(result.tables):
                table_info = {
                    "table_index": table_idx,
                    "row_count": table.row_count,
                    "column_count": table.column_count,
                    "cells": []
                }
                
                for cell in table.cells:
                    cell_info = {
                        "row_index": cell.row_index,
                        "column_index": cell.column_index,
                        "content": cell.content,
                        "confidence": cell.confidence if hasattr(cell, 'confidence') else None
                    }
                    table_info["cells"].append(cell_info)
                
                tables_info.append(table_info)
        
        # Extract key-value pairs if any
        key_value_pairs = []
        if result.key_value_pairs:
            for kv in result.key_value_pairs:
                kv_info = {
                    "key": kv.key.content if kv.key else "",
                    "value": kv.value.content if kv.value else "",
                    "confidence": kv.confidence if hasattr(kv, 'confidence') else None
                }
                key_value_pairs.append(kv_info)
        
        analysis_result = {
            "filename": filename,
            "full_text": full_text,
            "text_length": len(full_text),
            "pages": pages_info,
            "page_count": len(pages_info),
            "tables": tables_info,
            "table_count": len(tables_info),
            "key_value_pairs": key_value_pairs,
            "kv_pair_count": len(key_value_pairs),
            "analysis_timestamp": datetime.now().isoformat(),
            "model_used": self.model_id
        }
        
        logger.info(f"Extracted {len(full_text)} characters from {len(pages_info)} pages")
        print(f"🔍 DEBUG - Extraction complete: {len(full_text)} chars, {len(pages_info)} pages, {len(tables_info)} tables")
        
        return analysis_result


class AzureOpenAIClient:
    """
    Azure OpenAI client for field extraction and processing
    """
    
    def __init__(self):
        # Get configuration from centralized settings
        self.endpoint = AZURE_OPENAI_ENDPOINT
        self.api_key = AZURE_OPENAI_API_KEY
        self.api_version = AZURE_OPENAI_API_VERSION
        self.deployment_name = AZURE_OPENAI_DEPLOYMENT_NAME
        
        # Validate configuration
        if not all([self.endpoint, self.api_key, self.deployment_name]):
            raise ValueError("Azure OpenAI credentials not found in environment variables")
        
        # Initialize client
        openai.api_type = "azure"
        openai.api_base = self.endpoint
        openai.api_key = self.api_key
        openai.api_version = self.api_version
        
        logger.info(f"Azure OpenAI initialized with deployment: {self.deployment_name}")
        print(f"🔍 DEBUG - Azure OpenAI initialized: endpoint={self.endpoint[:50]}..., deployment={self.deployment_name}")
    
    async def extract_fields_from_text(self, extracted_text: str, language: str = "Hebrew") -> Dict[str, Any]:
        """
        Extract structured fields from OCR text using Azure OpenAI
        
        Args:
            extracted_text: Text extracted from Document Intelligence
            language: Document language (Hebrew/English)
            
        Returns:
            Dict with extracted fields in the required JSON format
        """
        logger.info(f"Starting field extraction from {len(extracted_text)} characters of text")
        print(f"🔍 DEBUG - Extracting fields from {len(extracted_text)} chars, language={language}")
        
        try:
            # Create prompt for field extraction
            prompt = self._create_extraction_prompt(extracted_text, language)
            
            print(f"🔍 DEBUG - Sending prompt to Azure OpenAI (length: {len(prompt)} chars)")
            
            # Call Azure OpenAI (using older openai version syntax)
            response = await asyncio.to_thread(
                openai.ChatCompletion.create,
                engine=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an expert at extracting structured information from Israeli National Insurance Institute forms. Extract information accurately and return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            # Extract response
            ai_response = response.choices[0].message.content
            print(f"🔍 DEBUG - Received AI response (length: {len(ai_response)} chars)")
            
            # Parse JSON response
            try:
                extracted_fields = json.loads(ai_response)
                logger.info("Successfully extracted fields using Azure OpenAI")
                return {
                    "extracted_fields": extracted_fields,
                    "extraction_successful": True,
                    "ai_response_length": len(ai_response),
                    "language_detected": language
                }
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI response as JSON: {e}")
                print(f"🔍 DEBUG - JSON parsing failed: {e}")
                return {
                    "extracted_fields": {},
                    "extraction_successful": False,
                    "error": f"JSON parsing error: {e}",
                    "raw_response": ai_response[:500] + "..." if len(ai_response) > 500 else ai_response
                }
                
        except Exception as e:
            logger.error(f"Field extraction failed: {e}")
            print(f"🔍 DEBUG - Field extraction FAILED: {str(e)}")
            return {
                "extracted_fields": {},
                "extraction_successful": False,
                "error": str(e)
            }
    
    def _create_extraction_prompt(self, text: str, language: str) -> str:
        """Create prompt for field extraction"""
        
        json_schema = """{
  "lastName": "",
  "firstName": "",
  "idNumber": "",
  "gender": "",
  "dateOfBirth": {
    "day": "",
    "month": "",
    "year": ""
  },
  "address": {
    "street": "",
    "houseNumber": "",
    "entrance": "",
    "apartment": "",
    "city": "",
    "postalCode": "",
    "poBox": ""
  },
  "landlinePhone": "",
  "mobilePhone": "",
  "jobType": "",
  "dateOfInjury": {
    "day": "",
    "month": "",
    "year": ""
  },
  "timeOfInjury": "",
  "accidentLocation": "",
  "accidentAddress": "",
  "accidentDescription": "",
  "injuredBodyPart": "",
  "signature": "",
  "formFillingDate": {
    "day": "",
    "month": "",
    "year": ""
  },
  "formReceiptDateAtClinic": {
    "day": "",
    "month": "",
    "year": ""
  },
  "medicalInstitutionFields": {
    "healthFundMember": "",
    "natureOfAccident": "",
    "medicalDiagnoses": ""
  }
}"""
        
        prompt = f"""
Extract information from this Israeli National Insurance Institute form text and return it in the exact JSON format specified.

Document Language: {language}
Document Text:
{text}

Required JSON Schema:
{json_schema}

Instructions:
1. Extract all available information from the text
2. For missing fields, use empty strings
3. For dates, extract day/month/year separately
4. For addresses, extract each component separately
5. Return ONLY valid JSON, no additional text
6. Handle both Hebrew and English text
7. For Israeli ID numbers, extract the 9-digit number
8. For health fund member (healthFundMember), look for מכבי, מאוחדת, כללית or Maccabi, Meuhedet, Clalit

Return only the JSON object:
"""
        
        return prompt


class IsraeliValidators:
    """
    Israeli-specific validation functions
    """
    
    @staticmethod
    def validate_israeli_id(id_number: str) -> Dict[str, Any]:
        """
        Validate Israeli ID number using checksum algorithm
        """
        print(f"🔍 DEBUG - Validating Israeli ID: {id_number}")
        
        if not id_number or not id_number.isdigit():
            return {"valid": False, "error": "ID must be digits only"}
        
        if len(id_number) != 9:
            return {"valid": False, "error": "ID must be exactly 9 digits"}
        
        # Israeli ID checksum algorithm
        total = 0
        for i, digit in enumerate(id_number[:8]):
            n = int(digit) * (2 if i % 2 == 1 else 1)
            total += n // 10 + n % 10
        
        checksum = (10 - (total % 10)) % 10
        is_valid = checksum == int(id_number[8])
        
        print(f"🔍 DEBUG - ID validation result: {is_valid}")
        
        return {
            "valid": is_valid,
            "error": None if is_valid else "Invalid Israeli ID checksum"
        }
    
    @staticmethod
    def validate_israeli_phone(phone: str) -> Dict[str, Any]:
        """
        Validate Israeli phone number format
        """
        if not phone:
            return {"valid": True, "error": None}  # Empty is OK
        
        # Remove spaces and dashes
        cleaned = re.sub(r'[-\s]', '', phone)
        
        # Israeli phone patterns
        patterns = [
            r'^0[2-4,8,9]\d{7}$',  # Landline: 02, 03, 04, 08, 09 + 7 digits
            r'^05[0-9]\d{7}$',     # Mobile: 050-059 + 7 digits
            r'^1[78]\d{2}$',       # Short numbers: 1700, 1800, etc.
        ]
        
        is_valid = any(re.match(pattern, cleaned) for pattern in patterns)
        
        return {
            "valid": is_valid,
            "error": None if is_valid else f"Invalid Israeli phone format: {phone}"
        }


# Utility functions for easy access
def get_document_intelligence_client() -> AzureDocumentIntelligence:
    """Get Azure Document Intelligence client"""
    return AzureDocumentIntelligence()

def get_markitdown_client() -> MarkItDownProcessor:
    """Get MarkItDown fallback processor"""
    return MarkItDownProcessor()

def get_openai_client() -> AzureOpenAIClient:
    """Get Azure OpenAI client"""
    return AzureOpenAIClient()
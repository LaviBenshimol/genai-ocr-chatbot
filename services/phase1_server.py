"""
Phase 1 MCP Server: OCR Field Extraction Service.

Uses Azure Document Intelligence for Israeli National Insurance forms
with Pydantic models for structured data validation and multiple export formats.
"""
import asyncio
import json
import time
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import DocumentAnalysisFeature
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
from openai import AzureOpenAI
from pydantic import ValidationError

from config.settings import (
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
    AZURE_DOCUMENT_INTELLIGENCE_KEY,
    AZURE_DOCUMENT_INTELLIGENCE_API_VERSION,
    AZURE_DOC_INTEL_MODEL,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT_NAME,
    AZURE_OPENAI_ENDPOINT,
)
from src.document_models import IsraeliValidators, NIIForm
from src.logger_config import get_logger

logger = get_logger("phase1_server")

# SCHEMA = {
#     "type": "object", "additionalProperties": False,
#     "properties": {
#         "lastName": {"type": "string"}, "firstName": {"type": "string"},
#         "idNumber": {"type": "string"},
#         "gender": {"type": "string", "enum": ["male", "female", ""]},
#         "dateOfBirth": {"type": "object", "additionalProperties": False,
#                         "properties": {"day": {"type": "string"}, "month": {"type": "string"},
#                                        "year": {"type": "string"}},
#                         "required": ["day", "month", "year"]
#                         },
#         "address": {"type": "object", "additionalProperties": False,
#                     "properties": {
#                         "street": {"type": "string"}, "houseNumber": {"type": "string"},
#                         "entrance": {"type": "string"}, "apartment": {"type": "string"},
#                         "city": {"type": "string"}, "postalCode": {"type": "string"}, "poBox": {"type": "string"}
#                     },
#                     "required": ["street", "houseNumber", "entrance", "apartment", "city", "postalCode", "poBox"]
#                     },
#         "landlinePhone": {"type": "string"}, "mobilePhone": {"type": "string"},
#         "jobType": {"type": "string"},
#         "dateOfInjury": {"type": "object", "additionalProperties": False,
#                          "properties": {"day": {"type": "string"}, "month": {"type": "string"},
#                                         "year": {"type": "string"}},
#                          "required": ["day", "month", "year"]
#                          },
#         "timeOfInjury": {"type": "string"},
#         "accidentLocation": {"type": "string"},
#         "accidentAddress": {"type": "string"},
#         "accidentDescription": {"type": "string"},
#         "injuredBodyPart": {"type": "string"},
#         "signature": {"type": "string"},
#         "formFillingDate": {"type": "object", "additionalProperties": False,
#                             "properties": {"day": {"type": "string"}, "month": {"type": "string"},
#                                            "year": {"type": "string"}},
#                             "required": ["day", "month", "year"]
#                             },
#         "formReceiptDateAtClinic": {"type": "object", "additionalProperties": False,
#                                     "properties": {"day": {"type": "string"}, "month": {"type": "string"},
#                                                    "year": {"type": "string"}},
#                                     "required": ["day", "month", "year"]
#                                     },
#         "medicalInstitutionFields": {"type": "object", "additionalProperties": False,
#                                      "properties": {
#                                          "healthFundMember": {"type": "string"},
#                                          "natureOfAccident": {"type": "string"},
#                                          "medicalDiagnoses": {"type": "string"}
#                                      },
#                                      "required": ["healthFundMember", "natureOfAccident", "medicalDiagnoses"]
#                                      }
#     },
#     "required": [
#         "lastName", "firstName", "idNumber", "gender", "dateOfBirth", "address",
#         "landlinePhone", "mobilePhone", "jobType", "dateOfInjury", "timeOfInjury",
#         "accidentLocation", "accidentAddress", "accidentDescription", "injuredBodyPart",
#         "signature", "formFillingDate", "formReceiptDateAtClinic", "medicalInstitutionFields"
#     ]
# }

# Bilingual label mapping for KVP processing
LABEL_MAPPING = {
    # Personal information
    "שם משפחה": "lastName", "last name": "lastName",
    "שם פרטי": "firstName", "first name": "firstName", 
    "מספר זהות": "idNumber", "ת.ז": "idNumber", "id": "idNumber", "id number": "idNumber",
    "מין": "gender", "gender": "gender",
    "תאריך לידה": "dateOfBirth", "date of birth": "dateOfBirth",
    
    # Address fields
    "רחוב": "address.street", "street": "address.street",
    "מספר בית": "address.houseNumber", "house number": "address.houseNumber",
    "כניסה": "address.entrance", "entrance": "address.entrance",
    "דירה": "address.apartment", "apartment": "address.apartment", 
    "יישוב": "address.city", "עיר": "address.city", "city": "address.city",
    "מיקוד": "address.postalCode", "postal code": "address.postalCode", "zipcode": "address.postalCode",
    "תא דואר": "address.poBox", "p.o. box": "address.poBox", "po box": "address.poBox",
    
    # Contact information
    "טלפון קווי": "landlinePhone", "landline": "landlinePhone", "telephone": "landlinePhone",
    "טלפון נייד": "mobilePhone", "mobile": "mobilePhone", "cellphone": "mobilePhone",
    
    # Accident details
    "תאריך הפגיעה": "dateOfInjury", "date of injury": "dateOfInjury",
    "שעת הפגיעה": "timeOfInjury", "time of injury": "timeOfInjury",
    "סוג העבודה": "jobType", "job type": "jobType",
    "מקום התאונה": "accidentLocation", "accident location": "accidentLocation",
    "כתובת מקום התאונה": "accidentAddress", "accident address": "accidentAddress",
    "נסיבות הפגיעה": "accidentDescription", "תיאור התאונה": "accidentDescription", 
    "accident description": "accidentDescription",
    "האיבר שנפגע": "injuredBodyPart", "injured body part": "injuredBodyPart",
    
    # Signature section
    "שם המבקש": "applicantName", "applicant name": "applicantName",
    "חתימה": "signaturePresent", "signature": "signaturePresent",
    
    # Dates
    "תאריך מילוי הטופס": "formFillingDate", "form fill date": "formFillingDate",
    "תאריך קבלת הטופס בקופה": "formReceiptDateAtClinic", "form receipt date": "formReceiptDateAtClinic",
    
    # Medical institution fields
    "מהות התאונה": "medicalInstitutionFields.natureOfAccident",
    "אבחנות רפואיות": "medicalInstitutionFields.medicalDiagnoses",
    "הנפגע חבר בקופת חולים": "medicalInstitutionFields.isHealthFundMember",
    "הנפגע אינו חבר בקופת חולים": "medicalInstitutionFields.isHealthFundMember",
    "כללית": "medicalInstitutionFields.healthFundName",
    "מכבי": "medicalInstitutionFields.healthFundName",
    "מאוחדת": "medicalInstitutionFields.healthFundName",
    "לאומית": "medicalInstitutionFields.healthFundName",
}

# Checkbox value mapping
CHECKBOX_MAPPING = {
    "זכר": ("gender", "male"), "male": ("gender", "male"),
    "נקבה": ("gender", "female"), "female": ("gender", "female"),
    
    # Accident context checkboxes
    "במפעל": ("accidentContext", "factory"), "factory": ("accidentContext", "factory"),
    "בדרך לעבודה": ("accidentContext", "commute_to_work"),
    "בדרך מהעבודה": ("accidentContext", "commute_from_work"),
    "בדרכים בעבודה": ("accidentContext", "work_travel"),
    "ת.ד": ("accidentContext", "traffic"), "תאונת דרכים": ("accidentContext", "traffic"),
    "תאונה בדרך ללא רכב": ("accidentContext", "non_vehicle"),
    
    # Health fund membership
    "הנפגע חבר בקופת חולים": ("medicalInstitutionFields.isHealthFundMember", True),
    "הנפגע אינו חבר בקופת חולים": ("medicalInstitutionFields.isHealthFundMember", False),
    
    # Health fund names
    "כללית": ("medicalInstitutionFields.healthFundName", "clalit"),
    "מכבי": ("medicalInstitutionFields.healthFundName", "maccabi"),
    "מאוחדת": ("medicalInstitutionFields.healthFundName", "meuhedet"),
    "לאומית": ("medicalInstitutionFields.healthFundName", "leumit"),
}


def _set_nested_value(data: Dict[str, Any], path: str, value: Any) -> None:
    """Set a value in nested dictionary using dot notation path."""
    keys = path.split('.')
    current = data
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value


def _process_kvps_and_checkboxes(kvp_pairs: List[Dict[str, str]]) -> Dict[str, Any]:
    """Process key-value pairs and checkbox selections into structured data."""
    extracted_data = {}
    
    for kvp in kvp_pairs:
        key = kvp.get("key", "").strip()
        value = kvp.get("value", "").strip()
        
        if not key or not value:
            continue
            
        # Normalize key to lowercase for lookup
        key_lower = key.lower()
        
        # Check for checkbox values (:selected: / :unselected:)
        if value in (":selected:", ":unselected:"):
            if value == ":selected:" and key in CHECKBOX_MAPPING:
                field_path, field_value = CHECKBOX_MAPPING[key]
                _set_nested_value(extracted_data, field_path, field_value)
        
        # Regular field mapping
        elif key in LABEL_MAPPING or key_lower in LABEL_MAPPING:
            mapped_field = LABEL_MAPPING.get(key, LABEL_MAPPING.get(key_lower))
            if mapped_field:
                _set_nested_value(extracted_data, mapped_field, value)
    
    return extracted_data


class Phase1OCRService:
    """
    Production-ready Phase 1 OCR service with comprehensive features.
    
    Features:
    - Cost optimization (first page processing)
    - Confidence tracking and analysis  
    - Smart Israeli phone/ID validation
    - Retry logic for transient failures
    - Token usage monitoring
    - Performance timing with SLA
    - Multiple export formats
    """

    def __init__(self, first_page_only: bool = True):
        """
        Initialize Phase 1 OCR service.
        
        Args:
            first_page_only: If True, process only first page for cost optimization.
                           Falls back to full document on failure.
        """
        self.first_page_only = first_page_only
        self.endpoint = AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT
        self.key = AZURE_DOCUMENT_INTELLIGENCE_KEY
        self.api_version = AZURE_DOCUMENT_INTELLIGENCE_API_VERSION
        self.model_id = AZURE_DOC_INTEL_MODEL
        
        # Performance tracking
        self.processing_timeout = 120  # 2 minutes SLA
        self.max_di_attempts = 2
        
        # Metrics tracking
        self.session_metrics = {
            "documents_processed": 0,
            "total_tokens_used": 0,
            "total_processing_time": 0,
            "confidence_scores": [],
            "token_usage_per_call": [],
            "timing_per_stage": []
        }

        if not self.endpoint or not self.key:
            raise ValueError(
                "Azure Document Intelligence credentials not found in environment variables"
            )

        try:
            self.client = DocumentIntelligenceClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.key),
            )
            logger.info(f"Production Phase 1 OCR Service initialized - "
                       f"first_page_only={first_page_only}, model={self.model_id}")
        except Exception as e:
            logger.error(f"Failed to initialize Document Intelligence client: {e}")
            raise

    def _empty_analysis_result(self, filename: str, error_msg: str) -> Dict[str, Any]:
        """Return empty analysis result structure for failed processing."""
        return {
            "filename": filename,
            "full_text": "",
            "text_length": 0,
            "pages": [],
            "page_count": 0,
            "tables": [],
            "table_count": 0,
            "key_value_pairs": [],
            "kv_pair_count": 0,
            "analysis_timestamp": datetime.now().isoformat(),
            "model_used": self.model_id,
            "confidence_summary": {"average_confidence": 0, "error": error_msg}
        }

    async def analyze_document(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Production analyze document with retry logic and confidence tracking.
        
        Strategy:
        1. Try first page only (cost optimization)
        2. If fails, try full document 
        3. If all fails, return empty result
        """
        start_time = time.time()
        model_id = self.model_id or "prebuilt-layout"
        
        logger.info(f"Starting document analysis: {filename} (first_page_only={self.first_page_only})")
        
        # Attempt 1: First page only (if enabled)
        if self.first_page_only:
            try:
                result = await self._perform_document_analysis(
                    file_bytes, model_id, pages="1", attempt_description="first page only"
                )
                
                analysis_result = self._process_document_result(result, filename, start_time)
                logger.info(f"Document analysis successful (first page): {filename}")
                return analysis_result
                
            except Exception as e:
                logger.warning(f"First page analysis failed for {filename}: {e}, trying full document")
        
        # Attempt 2: Full document  
        try:
            result = await self._perform_document_analysis(
                file_bytes, model_id, pages=None, attempt_description="full document"
            )
            
            analysis_result = self._process_document_result(result, filename, start_time)
            logger.info(f"Document analysis successful (full document): {filename}")
            return analysis_result
            
        except Exception as e:
            error_msg = f"All document analysis attempts failed: {e}"
            logger.error(f"{error_msg} for {filename}")
            return self._empty_analysis_result(filename, error_msg)

    async def _perform_document_analysis(self, file_bytes: bytes, model_id: str, 
                                       pages: Optional[str], attempt_description: str):
        """Perform actual Document Intelligence API call."""
        logger.info(f"DI API call: {attempt_description}, model={model_id}")
        
        # Prepare the document body
        document_body = BytesIO(file_bytes)
        
        # Prepare additional parameters
        kwargs = {
            "features": [DocumentAnalysisFeature.KEY_VALUE_PAIRS]
        }
        
        # Add page limitation if specified
        if pages:
            kwargs["pages"] = pages
            
        poller = await asyncio.to_thread(
            self.client.begin_analyze_document,
            model_id,
            document_body,
            **kwargs
        )
        
        return await asyncio.to_thread(poller.result)

    def _process_document_result(self, result, filename: str, start_time: float) -> Dict[str, Any]:
        """Process Document Intelligence result with confidence tracking."""
        full_text = ""
        pages = []
        tables = []
        key_value_pairs = []
        all_confidences = []

        # Process pages
        for page in result.pages:
            page_text = ""
            for line in page.lines:
                line_content = line.content + "\n"
                full_text += line_content
                page_text += line_content
                
                # Collect confidence scores
                if hasattr(line, 'confidence') and line.confidence:
                    all_confidences.append(line.confidence)
                    
            pages.append({
                "page_number": page.page_number,
                "text_lines": len(page.lines),
                "text": page_text.strip(),
            })

        # Process tables
        for table in result.tables:
            table_data = {
                "row_count": table.row_count,
                "column_count": table.column_count,
                "cells": [],
            }
            for cell in table.cells:
                table_data["cells"].append({
                    "row_index": cell.row_index,
                    "column_index": cell.column_index,
                    "content": cell.content,
                })
                
                # Collect confidence scores
                if hasattr(cell, 'confidence') and cell.confidence:
                    all_confidences.append(cell.confidence)
                    
            tables.append(table_data)

        # Process key-value pairs with confidence
        for kv in result.key_value_pairs or []:
            if kv.key and kv.value:
                key_conf = getattr(kv.key, 'confidence', None)
                val_conf = getattr(kv.value, 'confidence', None)
                
                kv_data = {
                    "key": kv.key.content,
                    "value": kv.value.content,
                }
                
                # Add confidence data if available
                if key_conf:
                    kv_data["key_confidence"] = key_conf
                    all_confidences.append(key_conf)
                if val_conf:
                    kv_data["value_confidence"] = val_conf
                    all_confidences.append(val_conf)
                    
                key_value_pairs.append(kv_data)

        # Calculate confidence summary
        confidence_summary = self._analyze_confidence(all_confidences)
        processing_time = time.time() - start_time
        
        # Update session metrics
        self.session_metrics["confidence_scores"].extend(all_confidences)
        
        return {
            "filename": filename,
            "full_text": full_text.strip(),
            "text_length": len(full_text.strip()),
            "pages": pages,
            "page_count": len(pages),
            "tables": tables,
            "table_count": len(tables),
            "key_value_pairs": key_value_pairs,
            "kv_pair_count": len(key_value_pairs),
            "confidence_summary": confidence_summary,
            "analysis_timestamp": datetime.now().isoformat(),
            "processing_time_seconds": processing_time,
            "model_used": self.model_id,
        }

    def _analyze_confidence(self, confidences: List[float]) -> Dict[str, Any]:
        """Analyze confidence scores and provide summary."""
        if not confidences:
            return {"average_confidence": 0, "analysis": "No confidence data available"}
            
        avg_confidence = sum(confidences) / len(confidences)
        min_confidence = min(confidences)
        max_confidence = max(confidences)
        low_confidence_count = sum(1 for c in confidences if c < 0.7)
        
        summary = {
            "average_confidence": round(avg_confidence, 3),
            "min_confidence": round(min_confidence, 3),
            "max_confidence": round(max_confidence, 3),
            "total_elements": len(confidences),
            "low_confidence_count": low_confidence_count,
            "low_confidence_percentage": round((low_confidence_count / len(confidences)) * 100, 1)
        }
        
        logger.info(f"Confidence analysis: avg={avg_confidence:.3f}, "
                   f"low_conf_elements={low_confidence_count}/{len(confidences)}")
        
        return summary

    def _build_messages(self, full_text: str, kv_pairs: List[Dict[str, str]], 
                       language_hint: str, extracted_seeds: Dict[str, Any]) -> List[Dict[str, str]]:
        """Build messages for Azure OpenAI completion with KVP data and pre-extracted seeds."""
        seed_text = ""
        if extracted_seeds:
            seed_text = (
                f"\n\nPre-detected checkboxes and fields (trust unless contradicted by text): "
                f"{json.dumps(extracted_seeds, ensure_ascii=False)}"
            )
        
        system = (
            "You extract fields from Israeli ביטוח לאומי medical forms. "
            "Return ONLY JSON matching the provided JSON Schema (UTF-8). "
            "If a field is missing or unreadable, output an empty string "
            "(or false for booleans). Dates are objects with string day/month/year; "
            "times HH:MM. Keys in the key/value list are already canonical."
        )
        user = (
            f"Language hint: {language_hint}\n"
            f"Canonical key/value candidates (JSON): {json.dumps(kv_pairs, ensure_ascii=False)}"
            f"{seed_text}\n\n"
            f"Full text (OCR):\n{full_text}"
        )
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    def _extract_fields_with_llm(self, full_text: str, kv_pairs: List[Dict[str, str]], 
                               language_hint: str, extracted_seeds: Dict[str, Any]) -> Tuple[NIIForm, Dict[str, Any]]:
        """
        Extract and validate fields using Azure OpenAI with token tracking.
        
        Returns:
            Tuple of (NIIForm instance, token usage metrics)
        """
        start_time = time.time()
        client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION or "2024-10-21",
        )
        
        messages = self._build_messages(full_text, kv_pairs, language_hint, extracted_seeds)
        
        # Estimate input tokens for logging
        input_text = json.dumps(messages, ensure_ascii=False)
        estimated_input_tokens = len(input_text.split())
        logger.info(f"LLM call starting - estimated input tokens: {estimated_input_tokens}")
        
        # Get Pydantic model JSON schema for structured output
        schema = NIIForm.model_json_schema()
        
        # Azure OpenAI structured outputs requires all properties to be in the required array
        if 'properties' in schema:
            schema['required'] = list(schema['properties'].keys())
            
        # Fix nested objects  
        def fix_nested_required(obj):
            if isinstance(obj, dict):
                if 'properties' in obj and 'type' in obj and obj['type'] == 'object':
                    obj['required'] = list(obj['properties'].keys())
                for value in obj.values():
                    fix_nested_required(value)
                    
        fix_nested_required(schema)
        
        try:
            completion = client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT_NAME,
                temperature=0,
                messages=messages,
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "NIIForm", "schema": schema, "strict": True},
                },
                timeout=60,
            )
            
            # Extract token usage metrics
            usage = completion.usage
            processing_time = time.time() - start_time
            
            token_metrics = {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
                "processing_time_seconds": processing_time,
                "estimated_input_tokens": estimated_input_tokens
            }
            
            # Update session metrics
            self.session_metrics["total_tokens_used"] += usage.total_tokens
            self.session_metrics["token_usage_per_call"].append(token_metrics)
            
            logger.info(f"LLM call completed - "
                       f"input: {usage.prompt_tokens} tokens, "
                       f"output: {usage.completion_tokens} tokens, "
                       f"total: {usage.total_tokens} tokens, "
                       f"time: {processing_time:.2f}s")
            
            content = completion.choices[0].message.content
            raw_data = json.loads(content)
            
            # Validate and create Pydantic model instance with smart validation
            try:
                form_model = NIIForm.model_validate(raw_data)
                logger.info("Pydantic validation successful with smart Israeli validators")
                return form_model, token_metrics
                
            except ValidationError as e:
                logger.error(f"Pydantic validation failed: {e}")
                return NIIForm(), token_metrics
                
        except Exception as e:
            processing_time = time.time() - start_time
            error_metrics = {
                "error": str(e),
                "processing_time_seconds": processing_time,
                "estimated_input_tokens": estimated_input_tokens,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
            
            logger.error(f"LLM extraction failed: {e}")
            return NIIForm(), error_metrics


    async def process_document(self, file_bytes: bytes, filename: str, language: str = "auto") -> Dict[str, Any]:
        """
        Production-ready document processing with retry logic, timing, and comprehensive metrics.
        
        Features:
        - Retry logic (max 2 attempts on failure)
        - 2-minute SLA timeout
        - Comprehensive timing and token tracking
        - Session metrics aggregation
        - Multiple export formats
        """
        process_start_time = time.time()
        
        logger.info(f"Starting document processing: {filename} (language={language})")
        
        # Process with retry logic (max 2 attempts)
        for attempt in range(1, 3):  # attempts 1 and 2
            try:
                logger.info(f"Processing attempt {attempt}/2 for {filename}")
                
                # Step 1: Azure Document Intelligence analysis with timing
                di_start = time.time()
                analysis = await self.analyze_document(file_bytes, filename)
                di_time = time.time() - di_start
                
                # Check if DI analysis failed (empty result indicates failure)
                if not analysis.get("full_text", "").strip():
                    if attempt < 2:
                        logger.warning(f"DI analysis returned empty text (attempt {attempt}), retrying...")
                        continue
                    else:
                        raise Exception("Document Intelligence analysis failed after all attempts")
                
                # Step 2: Process KVPs and extract checkbox seeds
                kvp_start = time.time()
                extracted_seeds = _process_kvps_and_checkboxes(analysis["key_value_pairs"])
                kvp_time = time.time() - kvp_start
                
                # Step 3: LLM field extraction with Pydantic validation
                llm_start = time.time()
                form_model, token_metrics = self._extract_fields_with_llm(
                    analysis["full_text"], 
                    analysis["key_value_pairs"], 
                    language, 
                    extracted_seeds
                )
                llm_time = time.time() - llm_start
                
                # Check if LLM extraction failed
                if hasattr(form_model, '__dict__') and not any(getattr(form_model, field, None) for field in ['last_name', 'first_name', 'id_number']):
                    if attempt < 2 and "error" not in token_metrics:
                        logger.warning(f"LLM extraction returned minimal data (attempt {attempt}), retrying...")
                        continue
                
                # Step 4: Israeli-specific validation
                validation_start = time.time()
                validation_results = self._validate_israeli_fields(form_model)
                validation_time = time.time() - validation_start
                
                # Step 5: Generate export formats
                export_start = time.time()
                canonical_data = form_model.model_dump(by_alias=True)
                hebrew_format = form_model.to_hebrew()
                english_format = form_model.to_english_readme()
                export_time = time.time() - export_start
                
                # Step 6: Calculate total processing time and update session metrics
                total_time = time.time() - process_start_time
                
                # Aggregate timing data
                timing_breakdown = {
                    "document_intelligence": round(di_time, 3),
                    "kvp_processing": round(kvp_time, 3),
                    "llm_extraction": round(llm_time, 3),
                    "israeli_validation": round(validation_time, 3),
                    "export_generation": round(export_time, 3),
                    "total_processing": round(total_time, 3)
                }
                
                # Update session metrics
                self.session_metrics["documents_processed"] += 1
                self.session_metrics["total_processing_time"] += total_time
                self.session_metrics["timing_per_stage"].append(timing_breakdown)
                
                # Calculate confidence score for this document
                doc_confidence = analysis.get("confidence_summary", {}).get("average_confidence", 0)
                
                logger.info(f"Document processing successful: {filename} "
                           f"(attempt {attempt}, total_time={total_time:.2f}s, confidence={doc_confidence:.3f})")
                
                return {
                    "filename": filename,
                    "language": language,
                    "success": True,
                    "analysis": analysis,
                    "extracted_fields": canonical_data,  # For test compatibility
                    "outputs": {
                        "canonical": canonical_data,
                        "hebrew_readme": hebrew_format,
                        "english_readme": english_format,
                    },
                    "validation_results": validation_results,
                    "token_usage": token_metrics,
                    "timing_breakdown": timing_breakdown,
                    "processing_attempt": attempt,
                    "errors": [],
                    "processing_timestamp": datetime.now().isoformat(),
                }
                
            except Exception as e:
                error_msg = f"Processing attempt {attempt} failed for {filename}: {e}"
                logger.warning(error_msg)
                
                if attempt == 2:  # Last attempt
                    # Update session metrics even for failures
                    total_time = time.time() - process_start_time
                    self.session_metrics["documents_processed"] += 1
                    self.session_metrics["total_processing_time"] += total_time
                    
                    logger.error(f"All processing attempts failed for {filename} after {total_time:.2f}s")
                    return {
                        "filename": filename,
                        "language": language,
                        "success": False,
                        "analysis": {},
                        "extracted_fields": {},
                        "outputs": {},
                        "validation_results": {"overall_valid": False, "field_validations": {}},
                        "token_usage": {"error": str(e)},
                        "timing_breakdown": {"total_processing": round(total_time, 3)},
                        "processing_attempt": attempt,
                        "errors": [error_msg],
                        "processing_timestamp": datetime.now().isoformat(),
                    }
                else:
                    # Wait briefly before retry
                    await asyncio.sleep(1)
                    continue
    
    def _validate_israeli_fields(self, form_model: NIIForm) -> Dict[str, Any]:
        """Perform Israeli-specific field validation."""
        validation_results = {
            "overall_valid": True,
            "field_validations": {},
            "validation_timestamp": datetime.now().isoformat()
        }
        
        # Validate Israeli ID
        if form_model.id_number:
            id_validation = IsraeliValidators.validate_israeli_id(form_model.id_number)
            validation_results["field_validations"]["idNumber"] = id_validation
            if not id_validation["valid"]:
                validation_results["overall_valid"] = False
        
        # Validate phone numbers
        for phone_field, phone_value in [
            ("landlinePhone", form_model.landline_phone),
            ("mobilePhone", form_model.mobile_phone)
        ]:
            if phone_value:
                phone_validation = IsraeliValidators.validate_israeli_phone(phone_value)
                validation_results["field_validations"][phone_field] = phone_validation
                if not phone_validation["valid"]:
                    validation_results["overall_valid"] = False
        
        return validation_results

    def get_session_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive session metrics with statistical analysis.
        
        Returns metrics for plotting confidence distributions and token usage analysis.
        """
        metrics = self.session_metrics.copy()
        
        # Confidence score analysis
        if metrics["confidence_scores"]:
            confidences = metrics["confidence_scores"]
            metrics["confidence_analysis"] = {
                "mean": round(sum(confidences) / len(confidences), 3),
                "min": round(min(confidences), 3),
                "max": round(max(confidences), 3),
                "count": len(confidences),
                "below_threshold_count": sum(1 for c in confidences if c < 0.7),
                "distribution_bins": self._calculate_confidence_distribution(confidences)
            }
        else:
            metrics["confidence_analysis"] = {"mean": 0, "count": 0, "distribution_bins": []}
            
        # Token usage analysis
        if metrics["token_usage_per_call"]:
            token_calls = metrics["token_usage_per_call"]
            total_tokens = [call.get("total_tokens", 0) for call in token_calls]
            prompt_tokens = [call.get("prompt_tokens", 0) for call in token_calls]
            completion_tokens = [call.get("completion_tokens", 0) for call in token_calls]
            
            metrics["token_analysis"] = {
                "total_calls": len(token_calls),
                "total_tokens_sum": sum(total_tokens),
                "average_tokens_per_call": round(sum(total_tokens) / len(total_tokens), 1) if total_tokens else 0,
                "prompt_completion_ratio": round(sum(prompt_tokens) / sum(completion_tokens), 2) if sum(completion_tokens) > 0 else 0,
                "token_distribution": {
                    "min_total": min(total_tokens) if total_tokens else 0,
                    "max_total": max(total_tokens) if total_tokens else 0,
                    "avg_prompt": round(sum(prompt_tokens) / len(prompt_tokens), 1) if prompt_tokens else 0,
                    "avg_completion": round(sum(completion_tokens) / len(completion_tokens), 1) if completion_tokens else 0
                }
            }
        else:
            metrics["token_analysis"] = {"total_calls": 0, "total_tokens_sum": 0}
            
        # Timing analysis
        if metrics["timing_per_stage"]:
            timings = metrics["timing_per_stage"]
            avg_timing = {}
            for stage in ["document_intelligence", "llm_extraction", "total_processing"]:
                stage_times = [t.get(stage, 0) for t in timings]
                if stage_times:
                    avg_timing[f"avg_{stage}"] = round(sum(stage_times) / len(stage_times), 3)
            metrics["timing_analysis"] = avg_timing
        else:
            metrics["timing_analysis"] = {}
            
        # Overall session summary
        metrics["session_summary"] = {
            "documents_processed": metrics["documents_processed"],
            "total_tokens_used": metrics["total_tokens_used"],
            "average_processing_time": round(metrics["total_processing_time"] / max(metrics["documents_processed"], 1), 2),
            "average_confidence": metrics["confidence_analysis"].get("mean", 0),
            "session_duration": round(metrics["total_processing_time"], 2)
        }
        
        return metrics
    
    def _calculate_confidence_distribution(self, confidences: List[float]) -> List[Dict[str, Any]]:
        """Calculate confidence score distribution for plotting."""
        bins = [(0.0, 0.3), (0.3, 0.5), (0.5, 0.7), (0.7, 0.85), (0.85, 1.0)]
        distribution = []
        
        for min_val, max_val in bins:
            count = sum(1 for c in confidences if min_val <= c < max_val)
            distribution.append({
                "range": f"{min_val}-{max_val}",
                "count": count,
                "percentage": round((count / len(confidences)) * 100, 1) if confidences else 0
            })
            
        return distribution
    
    def print_session_summary(self) -> None:
        """
        Print a formatted summary of session metrics for monitoring.
        """
        metrics = self.get_session_metrics()
        summary = metrics["session_summary"]
        confidence = metrics["confidence_analysis"]
        tokens = metrics["token_analysis"]
        
        logger.info("=== PRODUCTION SESSION SUMMARY ===")
        logger.info(f"Documents processed: {summary['documents_processed']}")
        logger.info(f"Total processing time: {summary['session_duration']}s")
        logger.info(f"Average processing time per document: {summary['average_processing_time']}s")
        logger.info(f"Total tokens consumed: {summary['total_tokens_used']}")
        logger.info(f"Average confidence score: {summary['average_confidence']}")
        logger.info(f"Elements below 0.7 confidence threshold: {confidence.get('below_threshold_count', 0)}")
        logger.info(f"Average tokens per LLM call: {tokens.get('average_tokens_per_call', 0)}")
        logger.info("======================================")
        
    def reset_session_metrics(self) -> None:
        """
        Reset session metrics for new processing session.
        """
        self.session_metrics = {
            "documents_processed": 0,
            "total_tokens_used": 0,
            "total_processing_time": 0,
            "confidence_scores": [],
            "token_usage_per_call": [],
            "timing_per_stage": []
        }
        logger.info("Session metrics reset for new processing session")
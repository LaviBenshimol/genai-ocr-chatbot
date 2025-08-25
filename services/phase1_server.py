"""
Phase 1 MCP Server: OCR Field Extraction Service
Uses Azure Document Intelligence for Israeli National Insurance forms
"""
import asyncio
import json
from datetime import datetime
from io import BytesIO
import re, math
from typing import Any, Dict, List, Tuple
from azure.core.exceptions import HttpResponseError

from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import DocumentAnalysisFeature
from openai import AzureOpenAI

from config.settings import (
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT_NAME,
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
    AZURE_DOCUMENT_INTELLIGENCE_KEY,
    AZURE_DOCUMENT_INTELLIGENCE_API_VERSION,
    AZURE_DOC_INTEL_MODEL,
)
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

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        # --- Header (section 0) ---
        "requestHeaderText": {"type": "string"},     # בקשה למתן טיפול רפואי...
        "destinationOrganization": {"type": "string"},  # אל קופ"ח/ביה"ח (free text)

        # --- Section 2 (personal) ---
        "lastName": {"type": "string"},
        "firstName": {"type": "string"},
        "idNumber": {"type": "string"},
        "gender": {"type": "string", "enum": ["male", "female", ""]},

        "dateOfBirth": {
            "type": "object", "additionalProperties": False,
            "properties": {"day": {"type": "string"}, "month": {"type": "string"}, "year": {"type": "string"}},
            "required": ["day", "month", "year"]
        },

        "address": {
            "type": "object", "additionalProperties": False,
            "properties": {
                "street": {"type": "string"},
                "houseNumber": {"type": "string"},
                "entrance": {"type": "string"},
                "apartment": {"type": "string"},
                "city": {"type": "string"},
                "postalCode": {"type": "string"},
                "poBox": {"type": "string"}
            },
            "required": ["street", "houseNumber", "entrance", "apartment", "city", "postalCode", "poBox"]
        },

        "landlinePhone": {"type": "string"},
        "mobilePhone": {"type": "string"},

        # --- Section 3 (accident) ---
        "jobType": {"type": "string"},
        "dateOfInjury": {
            "type": "object", "additionalProperties": False,
            "properties": {"day": {"type": "string"}, "month": {"type": "string"}, "year": {"type": "string"}},
            "required": ["day", "month", "year"]
        },
        "timeOfInjury": {"type": "string"},  # HH:MM

        "accidentLocation": {"type": "string"},
        "accidentAddress": {"type": "string"},
        "accidentDescription": {"type": "string"},
        "injuredBodyPart": {"type": "string"},

        # checkboxes in §3 (and a free-text "other")
        "accidentContext": {
            "type": "string",
            "enum": ["factory", "commute_to_work", "commute_from_work", "work_travel", "traffic", "non_vehicle", "", "other"]
        },
        "accidentContextOther": {"type": "string"},

        # --- Section 4 (signature/name) ---
        "applicantName": {"type": "string"},
        "signaturePresent": {"type": "boolean"},  # True if any mark/ink near חתימה

        # --- Dates in page header/footer (section 0) ---
        "formFillingDate": {
            "type": "object", "additionalProperties": False,
            "properties": {"day": {"type": "string"}, "month": {"type": "string"}, "year": {"type": "string"}},
            "required": ["day", "month", "year"]
        },
        "formReceiptDateAtClinic": {
            "type": "object", "additionalProperties": False,
            "properties": {"day": {"type": "string"}, "month": {"type": "string"}, "year": {"type": "string"}},
            "required": ["day", "month", "year"]
        },

        # --- Section 5 (clinic-only) ---
        "medicalInstitutionFields": {
            "type": "object", "additionalProperties": False,
            "properties": {
                "isHealthFundMember": {"type": "boolean"},
                "healthFundName": {"type": "string", "enum": ["clalit", "maccabi", "meuhedet", "leumit", ""]},
                "natureOfAccident": {"type": "string"},
                "medicalDiagnoses": {"type": "string"}
            },
            "required": ["isHealthFundMember", "healthFundName", "natureOfAccident", "medicalDiagnoses"]
        }
    },
    "required": [
        "lastName", "firstName", "idNumber", "gender", "dateOfBirth", "address",
        "landlinePhone", "mobilePhone", "jobType", "dateOfInjury", "timeOfInjury",
        "accidentLocation", "accidentAddress", "accidentDescription", "injuredBodyPart",
        "formFillingDate", "formReceiptDateAtClinic", "medicalInstitutionFields",
        "signaturePresent"  # present in output, True/False
    ]
}

class Phase1OCRService:
    """
    Azure Document Intelligence client for OCR processing.
    Handles PDF document analysis and text extraction.
    """

    def __init__(self):
        self.endpoint = AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT
        self.key = AZURE_DOCUMENT_INTELLIGENCE_KEY
        self.api_version = AZURE_DOCUMENT_INTELLIGENCE_API_VERSION
        self.model_id = AZURE_DOC_INTEL_MODEL

        if not self.endpoint or not self.key:
            raise ValueError(
                "Azure Document Intelligence credentials not found in environment variables"
            )

        try:
            self.client = DocumentIntelligenceClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.key),
                # api_version=self.api_version,  # default is 2024-11-30; keeping yours is fine
            )
            logger.info(f"Azure Document Intelligence initialized with model: {self.model_id}")
        except Exception as e:
            logger.error(f"Failed to initialize Document Intelligence client: {e}")
            raise

    async def analyze_document(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Analyze document using Azure Document Intelligence and return structured OCR data.
        """
        logger.info(f"Analyzing document: {filename}")
        try:
            model_id = self.model_id or "prebuilt-layout"
            try:
                # run the sync SDK call in a worker thread so we don't block the event loop
                poller = await asyncio.to_thread(
                    self.client.begin_analyze_document,
                    model_id,
                    BytesIO(file_bytes),  # <-- pass the bytes you received
                    features=[DocumentAnalysisFeature.KEY_VALUE_PAIRS],
                )
                result = await asyncio.to_thread(poller.result)
            except HttpResponseError as e:
                # Friendly fallback if someone configured a model that doesn't support KV
                if ("keyValuePairs" in str(e)) and (model_id != "prebuilt-layout"):
                    logger.warning("Retrying with prebuilt-layout due to keyValuePairs support.")
                    poller = await asyncio.to_thread(
                        self.client.begin_analyze_document,
                        "prebuilt-layout",
                        BytesIO(file_bytes),
                        features=[DocumentAnalysisFeature.KEY_VALUE_PAIRS],
                    )
                    result = await asyncio.to_thread(poller.result)
                else:
                    logger.error(f"Document analysis failed: {e}")
                    raise

            full_text = ""
            pages = []
            tables = []
            key_value_pairs = []

            for page in result.pages:
                page_text = ""
                for line in page.lines:
                    line_content = line.content + "\n"
                    full_text += line_content
                    page_text += line_content
                pages.append(
                    {
                        "page_number": page.page_number,
                        "text_lines": len(page.lines),
                        "text": page_text.strip(),
                    }
                )

            for table in result.tables:
                table_data = {
                    "row_count": table.row_count,
                    "column_count": table.column_count,
                    "cells": [],
                }
                for cell in table.cells:
                    table_data["cells"].append(
                        {
                            "row_index": cell.row_index,
                            "column_index": cell.column_index,
                            "content": cell.content,
                        }
                    )
                tables.append(table_data)

            for kv in result.key_value_pairs or []:
                if kv.key and kv.value:
                    key_value_pairs.append(
                        {
                            "key": kv.key.content,
                            "value": kv.value.content,
                        }
                    )

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
                "analysis_timestamp": datetime.now().isoformat(),
                "model_used": self.model_id,
            }
        except Exception as e:
            logger.error(f"OCR analysis failed for {filename}: {e}")
            raise

    def _build_messages(self, full_text: str, kv_pairs: list[dict], language_hint: str):
        system = (
            "You extract fields from Israeli ביטוח לאומי medical forms. "
            "Return ONLY the JSON that matches the provided JSON Schema. "
            "If a field is missing or unreadable, use an empty string. "
            "Normalize dates into day/month/year; times HH:MM; "
            "map Hebrew or English labels to the canonical JSON keys."
        )
        user = (
            f"Language hint: {language_hint}\n"
            f"Key/Value candidates (JSON): {json.dumps(kv_pairs, ensure_ascii=False)}\n\n"
            f"Full text:\n{full_text}"
        )
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    def _extract_fields_with_llm(self, full_text: str, kv_pairs: list[dict], language_hint: str = "auto"):
        client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,  # e.g. https://<resource>.openai.azure.com/
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION or "2024-10-21",
        )
        messages = self._build_messages(full_text, kv_pairs, language_hint)

        completion = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,  # <-- DEPLOYMENT NAME, not model name
            temperature=0,
            messages=messages,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "NIIForm", "schema": SCHEMA, "strict": True},
            },
        )
        content = completion.choices[0].message.content
        return json.loads(content)


    async def process_document(self, file_bytes: bytes, filename: str, language: str = "auto"):
        analysis = await self.analyze_document(file_bytes, filename)
        fields = self._extract_fields_with_llm(analysis["full_text"], analysis["key_value_pairs"], language)

        # minimal validation hook
        valid = True  # you can add checks here
        return {
            "filename": filename,
            "language": language,
            "success": True,
            "analysis": analysis,
            "extracted_fields": fields,
            "validation_results": {"overall_valid": valid, "field_validations": {}},
            "errors": [],
        }
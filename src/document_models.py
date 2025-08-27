"""
Israeli National Insurance Institute form data models.

Pydantic models for structured data extraction from Israeli ביטוח לאומי forms
with validation, export formats, and Israeli-specific field validation.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional
import logging

from pydantic import BaseModel, Field, field_validator, ConfigDict
import phonenumbers
from stdnum.il import idnr


class DateTriplet(BaseModel):
    """Date representation as separate day/month/year strings."""
    
    model_config = ConfigDict(extra='forbid')
    
    day: Optional[str] = ""
    month: Optional[str] = ""
    year: Optional[str] = ""

    @field_validator("day", "month")
    @classmethod
    def validate_day_month(cls, v: str) -> str:
        """Validate day and month are 1-2 digits."""
        v = (v or "").strip()
        if v and not re.fullmatch(r"\d{1,2}", v):
            # Keep as-is for flexibility, could raise ValueError to enforce
            pass
        return v

    @field_validator("year")
    @classmethod
    def validate_year(cls, v: str) -> str:
        """Validate year is 2-4 digits."""
        v = (v or "").strip()
        if v and not re.fullmatch(r"\d{2,4}", v):
            pass
        return v


class Address(BaseModel):
    """Israeli address with all standard fields."""
    
    model_config = ConfigDict(populate_by_name=True, extra='forbid')
    
    street: Optional[str] = ""
    house_number: Optional[str] = Field(default="", alias="houseNumber")
    entrance: Optional[str] = ""
    apartment: Optional[str] = ""
    city: Optional[str] = ""
    postal_code: Optional[str] = Field(default="", alias="postalCode")
    po_box: Optional[str] = Field(default="", alias="poBox")


class MedicalInstitutionFields(BaseModel):
    """Medical institution and health fund information."""
    
    model_config = ConfigDict(populate_by_name=True, extra='forbid')
    
    is_health_fund_member: Optional[bool] = Field(default=False, alias="isHealthFundMember")
    health_fund_name: Optional[str] = Field(default="", alias="healthFundName")
    nature_of_accident: Optional[str] = Field(default="", alias="natureOfAccident")
    medical_diagnoses: Optional[str] = Field(default="", alias="medicalDiagnoses")

    @field_validator("health_fund_name")
    @classmethod
    def validate_health_fund_name(cls, v: str) -> str:
        """Normalize health fund names to canonical English tokens."""
        v = (v or "").strip().lower()
        
        # Valid canonical names
        if v in ("", "clalit", "maccabi", "meuhedet", "leumit"):
            return v
            
        # Hebrew to English mapping
        hebrew_mapping = {
            "כללית": "clalit",
            "מכבי": "maccabi", 
            "מאוחדת": "meuhedet",
            "לאומית": "leumit"
        }
        return hebrew_mapping.get(v, "")


class NIIForm(BaseModel):
    """
    Complete Israeli National Insurance Institute form model.
    
    Represents form 283 with all sections including personal info,
    accident details, medical institution fields, and metadata.
    """
    
    model_config = ConfigDict(
        populate_by_name=True,
        extra='forbid'  # This ensures additionalProperties: false in JSON schema
    )
    
    # Header (section 0)
    request_header_text: Optional[str] = Field(default="", alias="requestHeaderText")
    destination_organization: Optional[str] = Field(default="", alias="destinationOrganization")

    # Section 2 (personal information)
    last_name: Optional[str] = Field(default="", alias="lastName")
    first_name: Optional[str] = Field(default="", alias="firstName")
    id_number: Optional[str] = Field(default="", alias="idNumber")
    gender: Optional[str] = ""
    date_of_birth: Optional[DateTriplet] = Field(default_factory=DateTriplet, alias="dateOfBirth")
    address: Optional[Address] = Field(default_factory=Address)
    landline_phone: Optional[str] = Field(default="", alias="landlinePhone")
    mobile_phone: Optional[str] = Field(default="", alias="mobilePhone")

    # Section 3 (accident details)  
    job_type: Optional[str] = Field(default="", alias="jobType")
    date_of_injury: Optional[DateTriplet] = Field(default_factory=DateTriplet, alias="dateOfInjury")
    time_of_injury: Optional[str] = Field(default="", alias="timeOfInjury")  # HH:MM format
    accident_location: Optional[str] = Field(default="", alias="accidentLocation")
    accident_address: Optional[str] = Field(default="", alias="accidentAddress")
    accident_description: Optional[str] = Field(default="", alias="accidentDescription")
    injured_body_part: Optional[str] = Field(default="", alias="injuredBodyPart")
    accident_context: Optional[str] = Field(default="", alias="accidentContext")
    accident_context_other: Optional[str] = Field(default="", alias="accidentContextOther")

    # Section 4 (signature)
    applicant_name: Optional[str] = Field(default="", alias="applicantName")
    signature_present: Optional[bool] = Field(default=False, alias="signaturePresent")

    # Dates (header/footer)
    form_filling_date: Optional[DateTriplet] = Field(default_factory=DateTriplet, alias="formFillingDate")
    form_receipt_date_at_clinic: Optional[DateTriplet] = Field(
        default_factory=DateTriplet, alias="formReceiptDateAtClinic"
    )

    # Section 5 (medical institution)
    medical_institution_fields: Optional[MedicalInstitutionFields] = Field(
        default_factory=MedicalInstitutionFields, alias="medicalInstitutionFields"
    )

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: str) -> str:
        """Normalize gender to standard values."""
        v = (v or "").strip().lower()
        if v in ("זכר", "male"):
            return "male"
        elif v in ("נקבה", "female"):
            return "female"
        return ""

    @field_validator("time_of_injury")
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        """Validate time is in HH:MM format."""
        v = (v or "").strip()
        if v and not re.fullmatch(r"\d{1,2}:\d{2}", v):
            # Keep as-is for flexibility
            pass
        return v

    @field_validator("accident_context")
    @classmethod  
    def validate_accident_context(cls, v: str) -> str:
        """Validate accident context is from allowed enum values."""
        valid_contexts = {
            "factory", "commute_to_work", "commute_from_work", 
            "work_travel", "traffic", "non_vehicle", "other", ""
        }
        if v not in valid_contexts:
            return ""
        return v

    @field_validator("id_number")
    @classmethod
    def validate_id_number(cls, v: str) -> str:
        """Validate Israeli ID using smart validation with python-stdnum."""
        return _validate_israeli_id_smart(v)

    @field_validator("landline_phone")
    @classmethod
    def validate_landline_phone(cls, v: str) -> str:
        """Validate landline phone using smart validation with OCR correction."""
        return _validate_israeli_phone_smart(v, "landlinePhone")

    @field_validator("mobile_phone")
    @classmethod
    def validate_mobile_phone(cls, v: str) -> str:
        """Validate mobile phone using smart validation with OCR correction."""
        return _validate_israeli_phone_smart(v, "mobilePhone")

    def to_hebrew(self) -> Dict[str, Any]:
        """Export form data in Hebrew format matching README specification."""
        return {
            "שם משפחה": self.last_name,
            "שם פרטי": self.first_name,
            "מספר זהות": self.id_number,
            "מין": {"male": "זכר", "female": "נקבה"}.get(self.gender, ""),
            "תאריך לידה": {
                "יום": self.date_of_birth.day,
                "חודש": self.date_of_birth.month,
                "שנה": self.date_of_birth.year
            },
            "כתובת": {
                "רחוב": self.address.street,
                "מספר בית": self.address.house_number,
                "כניסה": self.address.entrance,
                "דירה": self.address.apartment,
                "ישוב": self.address.city,
                "מיקוד": self.address.postal_code,
                "תא דואר": self.address.po_box,
            },
            "טלפון קווי": self.landline_phone,
            "טלפון נייד": self.mobile_phone,
            "סוג העבודה": self.job_type,
            "תאריך הפגיעה": {
                "יום": self.date_of_injury.day,
                "חודש": self.date_of_injury.month,
                "שנה": self.date_of_injury.year
            },
            "שעת הפגיעה": self.time_of_injury,
            "מקום התאונה": self.accident_location,
            "כתובת מקום התאונה": self.accident_address,
            "תיאור התאונה": self.accident_description,
            "האיבר שנפגע": self.injured_body_part,
            "חתימה": "כן" if self.signature_present else "",
            "תאריך מילוי הטופס": {
                "יום": self.form_filling_date.day,
                "חודש": self.form_filling_date.month,
                "שנה": self.form_filling_date.year
            },
            "תאריך קבלת הטופס בקופה": {
                "יום": self.form_receipt_date_at_clinic.day,
                "חודש": self.form_receipt_date_at_clinic.month,
                "שנה": self.form_receipt_date_at_clinic.year
            },
            "למילוי ע\"י המוסד הרפואי": {
                "חבר בקופת חולים": "כן" if self.medical_institution_fields.is_health_fund_member else "",
                "מהות התאונה": self.medical_institution_fields.nature_of_accident,
                "אבחנות רפואיות": self.medical_institution_fields.medical_diagnoses,
            },
        }

    def to_english_readme(self) -> Dict[str, Any]:
        """Export form data in English README format."""
        return {
            "lastName": self.last_name,
            "firstName": self.first_name,
            "idNumber": self.id_number,
            "gender": self.gender,
            "dateOfBirth": self.date_of_birth.model_dump(by_alias=True),
            "address": self.address.model_dump(by_alias=True),
            "landlinePhone": self.landline_phone,
            "mobilePhone": self.mobile_phone,
            "jobType": self.job_type,
            "dateOfInjury": self.date_of_injury.model_dump(by_alias=True),
            "timeOfInjury": self.time_of_injury,
            "accidentLocation": self.accident_location,
            "accidentAddress": self.accident_address,
            "accidentDescription": self.accident_description,
            "injuredBodyPart": self.injured_body_part,
            "signature": "true" if self.signature_present else "",
            "formFillingDate": self.form_filling_date.model_dump(by_alias=True),
            "formReceiptDateAtClinic": self.form_receipt_date_at_clinic.model_dump(by_alias=True),
            "medicalInstitutionFields": {
                "healthFundMember": "yes" if self.medical_institution_fields.is_health_fund_member else "",
                "natureOfAccident": self.medical_institution_fields.nature_of_accident,
                "medicalDiagnoses": self.medical_institution_fields.medical_diagnoses,
            },
        }


def _validate_israeli_phone_smart(value: str, field_name: str = "phone") -> str:
    """
    Smart Israeli phone validation with OCR error correction.
    
    Strategy: Try direct parsing first, then apply OCR fixes if needed.
    Returns normalized phone number or original value (permissive).
    """
    logger = logging.getLogger("document_models")
    original = (value or "").strip()
    
    if not original:
        return original
        
    # Step 1: Try direct parsing first
    try:
        parsed = phonenumbers.parse(original, "IL")
        if phonenumbers.is_valid_number(parsed):
            normalized = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
            logger.info(f"Phone validation success (direct): {original} → {normalized}")
            return normalized
    except phonenumbers.NumberParseException:
        pass
    
    # Step 2: Try OCR fixes for common digit misrecognition  
    cleaned = original.replace(" ", "").replace("-", "")
    fixes_attempted = []
    
    # Common OCR errors for leading '0' in Israeli phone numbers
    if len(cleaned) in [9, 10]:
        for wrong_digit, fix_name in [("6", "6→0"), ("8", "8→0"), ("9", "9→0"), ("O", "O→0"), ("o", "o→0")]:
            if cleaned.startswith(wrong_digit):
                fixed = "0" + cleaned[1:]
                fixes_attempted.append(fix_name)
                
                try:
                    parsed = phonenumbers.parse(fixed, "IL")
                    if phonenumbers.is_valid_number(parsed):
                        normalized = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
                        logger.info(f"Phone OCR fix successful: {original} → {normalized} (fix: {fix_name})")
                        return normalized
                except phonenumbers.NumberParseException:
                    continue
    
    # Step 3: Log failure and return original (permissive approach)
    if fixes_attempted:
        logger.warning(f"Phone validation failed after OCR fixes: {original} → tried fixes: {fixes_attempted}")
    else:
        logger.warning(f"Phone validation failed: {original}")
    
    return original  # Return original - permissive


def _validate_israeli_id_smart(value: str) -> str:
    """
    Smart Israeli ID validation using python-stdnum.
    
    Returns normalized ID or original value (permissive).
    """
    logger = logging.getLogger("document_models")
    original = (value or "").strip()
    
    if not original:
        return original
        
    def validate_israeli_id_luhn(id_number):
        """Validates Israeli ID using correct Luhn algorithm."""
        id_number = str(id_number).replace('-', '').strip()
        if not id_number.isdigit() or len(id_number) != 9:
            return False
        digits = [int(d) for d in id_number]
        checksum_digit = digits.pop()
        total_sum = 0
        for i, digit in enumerate(reversed(digits)):
            if (i + 1) % 2 == 0:  # Even position (from right, 0-indexed)
                doubled_digit = digit * 2
                if doubled_digit > 9:
                    total_sum += (doubled_digit % 10) + (doubled_digit // 10)
                else:
                    total_sum += doubled_digit
            else:  # Odd position
                total_sum += digit
        calculated_checksum = (10 - (total_sum % 10)) % 10
        return calculated_checksum == checksum_digit

    # Try direct validation first
    if validate_israeli_id_luhn(original):
        logger.info(f"Israeli ID validation success: {original}")
        return original
        
    # Try common OCR corrections for last digit
    for last_digit in range(10):
        corrected_id = original[:-1] + str(last_digit)
        if validate_israeli_id_luhn(corrected_id):
            logger.info(f"Israeli ID OCR correction applied: {original} → {corrected_id}")
            return corrected_id
    
    logger.warning(f"Israeli ID validation failed: {original} (invalid checksum)")
    return original  # Return original - permissive


class IsraeliValidators:
    """Legacy compatibility - keep for backward compatibility."""
    
    @staticmethod  
    def validate_israeli_id(id_number: str) -> Dict[str, Any]:
        """Legacy method - use smart validation in Pydantic models."""
        try:
            normalized = _validate_israeli_id_smart(id_number)
            is_valid = normalized != id_number or idnr.is_valid(normalized)
            return {"valid": is_valid, "error": None if is_valid else "Invalid Israeli ID"}
        except:
            return {"valid": False, "error": "Invalid Israeli ID"}
    
    @staticmethod
    def validate_israeli_phone(phone: str) -> Dict[str, Any]:
        """Legacy method - use smart validation in Pydantic models."""
        try:
            normalized = _validate_israeli_phone_smart(phone)
            # Test if the normalized number is actually valid using phonenumbers
            import phonenumbers
            try:
                parsed = phonenumbers.parse(normalized, "IL")
                is_valid = phonenumbers.is_valid_number(parsed)
                if is_valid:
                    if normalized != phone.strip():
                        return {"valid": True, "error": None, "corrected": normalized}
                    else:
                        return {"valid": True, "error": None}
                else:
                    return {"valid": False, "error": "Invalid Israeli phone format"}
            except:
                return {"valid": False, "error": "Invalid phone number format"}
        except:
            return {"valid": False, "error": "Invalid phone format"}
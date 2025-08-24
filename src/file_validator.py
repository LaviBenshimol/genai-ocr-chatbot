"""
File Validation System for OCR Document Upload
Handles file type, size, and content validation before MCP server processing
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import io
import PyPDF2
from PIL import Image

# Set up logging
logger = logging.getLogger(__name__)

class FileValidationError(Exception):
    """Custom exception for file validation errors"""
    pass

class FileValidator:
    """
    Validates uploaded files before OCR processing
    - File type validation (PDF only for production)
    - File size limits
    - PDF page limits  
    - Content validation
    """
    
    def __init__(self):
        # File constraints
        self.MAX_FILE_SIZE_MB = 5   # 5MB limit
        self.MAX_PDF_PAGES = 2      # 2 pages max for OCR processing
        self.ALLOWED_EXTENSIONS = {'.pdf'}  # Only PDF for production
        
        # File type mappings
        self.MIME_TYPES = {
            'application/pdf': '.pdf',
            'image/jpeg': '.jpg',
            'image/jpg': '.jpg', 
            'image/png': '.png'
        }
        
        logger.info("File validator initialized with PDF-only restrictions")
        # DEBUG: Print validation settings
        print(f"🔍 DEBUG - File validator settings: MAX_SIZE={self.MAX_FILE_SIZE_MB}MB, MAX_PAGES={self.MAX_PDF_PAGES}, ALLOWED={self.ALLOWED_EXTENSIONS}")
    
    def validate_file(self, uploaded_file) -> Dict:
        """
        Main validation method for uploaded files
        Args:
            uploaded_file: Streamlit uploaded file object
        Returns:
            Dict with validation results and file info
        Raises:
            FileValidationError: If validation fails
        """
        # DEBUG: Print uploaded file details  
        print(f"🔍 DEBUG - Validating file: {uploaded_file.name}, size={uploaded_file.size} bytes, type={uploaded_file.type}")
        logger.info(f"Starting validation for file: {uploaded_file.name}")
        
        validation_result = {
            "is_valid": False,
            "file_info": {},
            "validation_checks": {},
            "errors": [],
            "warnings": []
        }
        
        try:
            # Extract basic file info
            file_info = self._extract_file_info(uploaded_file)
            validation_result["file_info"] = file_info

            logger.info(f"File info extracted: {file_info['name']}, {file_info['size_mb']:.2f}MB, {file_info['extension']}")
            
            # Run validation checks
            checks = self._run_validation_checks(uploaded_file, file_info)
            validation_result["validation_checks"] = checks
            
            # Collect errors and warnings
            errors = []
            warnings = []
            
            for check_name, check_result in checks.items():
                if not check_result["passed"]:
                    if check_result["severity"] == "error":
                        errors.append(f"{check_name}: {check_result['message']}")
                    else:
                        warnings.append(f"{check_name}: {check_result['message']}")
            
            validation_result["errors"] = errors
            validation_result["warnings"] = warnings
            validation_result["is_valid"] = len(errors) == 0
            
            # Log results
            if validation_result["is_valid"]:
                logger.info(f"File validation PASSED: {uploaded_file.name}")
                if warnings:
                    logger.warning(f"File has warnings: {'; '.join(warnings)}")
            else:
                logger.error(f"File validation FAILED: {uploaded_file.name} - Errors: {'; '.join(errors)}")
            

            return validation_result
            
        except Exception as e:
            logger.error(f"Unexpected error during file validation: {e}")
            validation_result["errors"] = [f"Validation error: {str(e)}"]
            return validation_result
    
    def _extract_file_info(self, uploaded_file) -> Dict:
        """Extract basic information from uploaded file"""

        file_extension = Path(uploaded_file.name).suffix.lower()
        size_bytes = uploaded_file.size
        size_mb = size_bytes / (1024 * 1024)
        
        return {
            "name": uploaded_file.name,
            "extension": file_extension,
            "mime_type": uploaded_file.type,
            "size_bytes": size_bytes,
            "size_mb": size_mb
        }
    
    def _run_validation_checks(self, uploaded_file, file_info: Dict) -> Dict:
        """Run all validation checks"""

        checks = {}
        
        # 1. File extension check
        checks["extension"] = self._check_file_extension(file_info["extension"])
        
        # 2. MIME type check
        checks["mime_type"] = self._check_mime_type(file_info["mime_type"], file_info["extension"])
        
        # 3. File size check
        checks["file_size"] = self._check_file_size(file_info["size_mb"])
        
        # 4. Content validation (PDF specific)
        if file_info["extension"] == ".pdf":
            checks["pdf_content"] = self._check_pdf_content(uploaded_file)
            checks["pdf_pages"] = self._check_pdf_pages(uploaded_file)
        
        # 5. File name validation
        checks["filename"] = self._check_filename(file_info["name"])
        
        return checks
    
    def _check_file_extension(self, extension: str) -> Dict:
        """Check if file extension is allowed"""

        if extension in self.ALLOWED_EXTENSIONS:
            return {
                "passed": True,
                "message": f"File extension {extension} is allowed",
                "severity": "info"
            }
        else:
            return {
                "passed": False,
                "message": f"File extension {extension} not allowed. Only PDF files are supported.",
                "severity": "error"
            }
    
    def _check_mime_type(self, mime_type: str, extension: str) -> Dict:
        """Check if MIME type matches extension"""

        expected_extension = self.MIME_TYPES.get(mime_type)
        
        if expected_extension == extension:
            return {
                "passed": True,
                "message": f"MIME type {mime_type} matches extension {extension}",
                "severity": "info"
            }
        else:
            return {
                "passed": False,
                "message": f"MIME type {mime_type} doesn't match extension {extension}",
                "severity": "error"
            }
    
    def _check_file_size(self, size_mb: float) -> Dict:
        """Check if file size is within limits"""

        if size_mb <= self.MAX_FILE_SIZE_MB:
            return {
                "passed": True,
                "message": f"File size {size_mb:.2f}MB is within {self.MAX_FILE_SIZE_MB}MB limit",
                "severity": "info"
            }
        else:
            return {
                "passed": False,
                "message": f"File size {size_mb:.2f}MB exceeds {self.MAX_FILE_SIZE_MB}MB limit",
                "severity": "error"
            }
    
    def _check_pdf_content(self, uploaded_file) -> Dict:
        """Validate PDF file content"""

        try:
            # Reset file pointer
            uploaded_file.seek(0)
            
            # Try to read PDF
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.read()))
            
            # Reset file pointer again
            uploaded_file.seek(0)
            
            # Check if PDF is readable
            if len(pdf_reader.pages) > 0:
                # Try to extract text from first page to verify readability
                first_page = pdf_reader.pages[0]
                text = first_page.extract_text()
                
                return {
                    "passed": True,
                    "message": f"PDF is readable with {len(pdf_reader.pages)} pages",
                    "severity": "info"
                }
            else:
                return {
                    "passed": False,
                    "message": "PDF appears to be empty or corrupted",
                    "severity": "error"
                }
                
        except Exception as e:
            return {
                "passed": False,
                "message": f"PDF validation failed: {str(e)}",
                "severity": "error"
            }
    
    def _check_pdf_pages(self, uploaded_file) -> Dict:
        """Check PDF page count"""

        try:
            uploaded_file.seek(0)
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.read()))
            uploaded_file.seek(0)
            
            page_count = len(pdf_reader.pages)
            
            if page_count <= self.MAX_PDF_PAGES:
                return {
                    "passed": True,
                    "message": f"PDF has {page_count} pages (within {self.MAX_PDF_PAGES} page limit)",
                    "severity": "info"
                }
            else:
                return {
                    "passed": False,
                    "message": f"PDF has {page_count} pages (exceeds {self.MAX_PDF_PAGES} page limit)",
                    "severity": "error"
                }
                
        except Exception as e:
            return {
                "passed": False,
                "message": f"Could not count PDF pages: {str(e)}",
                "severity": "error"
            }
    
    def _check_filename(self, filename: str) -> Dict:
        """Check filename for security issues"""

        # Basic security checks
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/', '..']
        
        if any(char in filename for char in dangerous_chars):
            return {
                "passed": False,
                "message": f"Filename contains dangerous characters",
                "severity": "error"
            }
        
        if len(filename) > 255:
            return {
                "passed": False,
                "message": f"Filename is too long (max 255 characters)",
                "severity": "error"
            }
        
        return {
            "passed": True,
            "message": "Filename is valid",
            "severity": "info"
        }


# Utility function
def validate_uploaded_file(uploaded_file) -> Dict:
    """Convenience function for file validation"""
    validator = FileValidator()
    return validator.validate_file(uploaded_file)
"""
Phase 1 UI: OCR Field Extraction Interface
Handles file upload, processing, and display of extracted fields
"""

import streamlit as st
import json
from pathlib import Path
import sys

# Add project paths
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def render_phase1(demo_mode=True):
    """Render Phase 1 OCR interface"""
    
    st.header("📄 Phase 1: OCR Field Extraction")
    st.markdown("Extract structured information from National Insurance Institute forms")
    
    # Create columns for layout
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📤 Document Upload")
        
        # File uploader - PDF only for production
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type=['pdf'],
            help="Upload National Insurance Institute forms in PDF format only"
        )
        
        if uploaded_file is not None:
            # DEBUG: Log uploaded file details
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"DEBUG - File uploaded: name={uploaded_file.name}, size={uploaded_file.size}, type={uploaded_file.type}")
            print(f"🔍 DEBUG - Uploaded file object: {type(uploaded_file)}, name={uploaded_file.name}")
            
            # DEBUG: Show debug info in Streamlit UI
            with st.expander("🐛 Debug Information", expanded=False):
                st.write("**File Upload Debug:**")
                st.write(f"- File name: `{uploaded_file.name}`")
                st.write(f"- File size: `{uploaded_file.size} bytes`")
                st.write(f"- File type: `{uploaded_file.type}`")
                st.write(f"- File object type: `{type(uploaded_file)}`")
                st.write(f"- Demo mode: `{demo_mode}`")
            
            # Import file validator
            from src.file_validator import validate_uploaded_file
            
            with st.spinner("🔍 Validating file..."):
                # Validate the uploaded file
                validation_result = validate_uploaded_file(uploaded_file)
                
                # DEBUG: Log validation result
                logger.info(f"DEBUG - Validation result: valid={validation_result['is_valid']}, errors={len(validation_result['errors'])}")
                print(f"🔍 DEBUG - Validation passed: {validation_result['is_valid']}")
                if not validation_result['is_valid']:
                    print(f"🔍 DEBUG - Validation errors: {validation_result['errors']}")
            
            if validation_result["is_valid"]:
                st.success(f"✅ File validated: {uploaded_file.name}")
                
                # Display file info
                file_info = validation_result["file_info"]
                file_details = {
                    "Filename": file_info["name"],
                    "File size": f"{file_info['size_mb']:.2f} MB ({file_info['size_bytes']} bytes)",
                    "File type": file_info["mime_type"],
                    "Extension": file_info["extension"]
                }
                
                with st.expander("📋 File Details"):
                    for key, value in file_details.items():
                        st.write(f"**{key}**: {value}")
                
                # Display validation checks
                with st.expander("✅ Validation Results"):
                    for check_name, check_result in validation_result["validation_checks"].items():
                        if check_result["passed"]:
                            st.success(f"✅ {check_name}: {check_result['message']}")
                        else:
                            st.error(f"❌ {check_name}: {check_result['message']}")
                
                # Store validated file in session state for processing
                st.session_state['validated_file'] = uploaded_file
                st.session_state['file_validation'] = validation_result
                
            else:
                st.error(f"❌ File validation failed: {uploaded_file.name}")
                
                # Display validation errors
                for error in validation_result["errors"]:
                    st.error(f"🚫 {error}")
                
                # Display warnings if any
                for warning in validation_result["warnings"]:
                    st.warning(f"⚠️ {warning}")
                
                # Display detailed validation checks
                with st.expander("🔍 Detailed Validation Results"):
                    for check_name, check_result in validation_result["validation_checks"].items():
                        if check_result["passed"]:
                            st.success(f"✅ {check_name}: {check_result['message']}")
                        else:
                            if check_result["severity"] == "error":
                                st.error(f"❌ {check_name}: {check_result['message']}")
                            else:
                                st.warning(f"⚠️ {check_name}: {check_result['message']}")
                
                # Clear any previous validated file
                if 'validated_file' in st.session_state:
                    del st.session_state['validated_file']
                if 'file_validation' in st.session_state:
                    del st.session_state['file_validation']
        
        # Language selection
        st.subheader("🌐 Language Settings")
        language = st.selectbox(
            "Form Language",
            ["Hebrew", "English", "Auto-detect"],
            index=2
        )
        
        # Processing button - only enabled for validated files
        has_validated_file = 'validated_file' in st.session_state and st.session_state.get('validated_file') is not None
        
        process_button = st.button(
            "🚀 Extract Fields",
            disabled=not has_validated_file,
            type="primary",
            help="File must be validated before processing"
        )
        
        if not has_validated_file and uploaded_file is not None:
            st.info("📋 Please wait for file validation to complete before processing.")
        
        if process_button and has_validated_file:

            validated_file = st.session_state['validated_file']
            file_validation = st.session_state['file_validation']
            
            with st.spinner("🔄 Processing document..."):

                # Log the processing start
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Starting OCR processing for validated file: {validated_file.name}")
                
                # Simulate processing time
                import time
                time.sleep(2)
                
                if demo_mode:
                    # Load mock response with file info
                    mock_response = get_mock_extraction_result()
                    mock_response['processed_file'] = file_validation['file_info']
                    mock_response['validation_passed'] = True
                    
                    st.session_state['extraction_result'] = mock_response
                    st.success("✅ Fields extracted successfully from validated file!")
                    
                    logger.info(f"Mock OCR processing completed for: {validated_file.name}")
                    
                else:
                    st.error("🔴 Production mode not yet implemented - will call Phase 1 MCP server")
                    logger.warning("Production mode called but not yet implemented")
    
    with col2:
        st.subheader("📊 Extraction Results")
        
        if 'extraction_result' in st.session_state:
            result = st.session_state['extraction_result']
            
            # Display confidence score if available
            if 'confidence' in result:
                confidence = result['confidence']
                st.metric("Confidence Score", f"{confidence:.1%}")
            
            # Tabbed display of results
            tab1, tab2, tab3 = st.tabs(["🔍 Formatted View", "📄 JSON Output", "✅ Validation"])
            
            with tab1:
                display_formatted_results(result.get('extracted_fields', {}))
            
            with tab2:
                st.json(result.get('extracted_fields', {}))
                
                # Download button for JSON
                json_str = json.dumps(result.get('extracted_fields', {}), ensure_ascii=False, indent=2)
                st.download_button(
                    label="⬇️ Download JSON",
                    data=json_str,
                    file_name="extracted_fields.json",
                    mime="application/json"
                )
            
            with tab3:
                display_validation_results(result.get('validation', {}))
        
        else:
            st.info("👆 Upload a document and click 'Extract Fields' to see results")

def display_formatted_results(fields):
    """Display extraction results in a formatted view"""
    
    if not fields:
        st.warning("No fields extracted")
        return
    
    # Personal Information
    st.subheader("👤 Personal Information")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**Last Name**: {fields.get('lastName', 'N/A')}")
        st.write(f"**First Name**: {fields.get('firstName', 'N/A')}")
        st.write(f"**ID Number**: {fields.get('idNumber', 'N/A')}")
        st.write(f"**Gender**: {fields.get('gender', 'N/A')}")
    
    with col2:
        dob = fields.get('dateOfBirth', {})
        if dob:
            dob_str = f"{dob.get('day', '')}/{dob.get('month', '')}/{dob.get('year', '')}"
            st.write(f"**Date of Birth**: {dob_str}")
        
        st.write(f"**Mobile Phone**: {fields.get('mobilePhone', 'N/A')}")
        st.write(f"**Landline Phone**: {fields.get('landlinePhone', 'N/A')}")
    
    # Address Information
    st.subheader("🏠 Address Information")
    address = fields.get('address', {})
    if address:
        address_parts = []
        if address.get('street'): address_parts.append(address['street'])
        if address.get('houseNumber'): address_parts.append(address['houseNumber'])
        if address.get('city'): address_parts.append(address['city'])
        
        full_address = ", ".join(address_parts) if address_parts else "N/A"
        st.write(f"**Full Address**: {full_address}")
        st.write(f"**Postal Code**: {address.get('postalCode', 'N/A')}")
    
    # Incident Information
    st.subheader("⚡ Incident Information")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**Job Type**: {fields.get('jobType', 'N/A')}")
        
        injury_date = fields.get('dateOfInjury', {})
        if injury_date:
            injury_date_str = f"{injury_date.get('day', '')}/{injury_date.get('month', '')}/{injury_date.get('year', '')}"
            st.write(f"**Date of Injury**: {injury_date_str}")
        
        st.write(f"**Time of Injury**: {fields.get('timeOfInjury', 'N/A')}")
    
    with col2:
        st.write(f"**Accident Location**: {fields.get('accidentLocation', 'N/A')}")
        st.write(f"**Injured Body Part**: {fields.get('injuredBodyPart', 'N/A')}")
    
    # Accident Description
    if fields.get('accidentDescription'):
        st.subheader("📝 Accident Description")
        st.text_area(
            "Description",
            value=fields['accidentDescription'],
            disabled=True,
            height=100
        )

def display_validation_results(validation):
    """Display field validation results"""
    
    if not validation:
        st.info("No validation information available")
        return
    
    # Overall validation status
    overall_valid = validation.get('is_valid', False)
    if overall_valid:
        st.success("✅ All extracted fields are valid")
    else:
        st.warning("⚠️ Some fields may need attention")
    
    # Field-specific validation
    field_validations = validation.get('field_validation', {})
    if field_validations:
        st.subheader("Field Validation Details")
        
        for field, status in field_validations.items():
            if status['valid']:
                st.success(f"✅ {field}: Valid")
            else:
                st.error(f"❌ {field}: {status.get('error', 'Invalid')}")

def get_mock_extraction_result():
    """Return mock extraction result for demo"""
    return {
        "confidence": 0.89,
        "extracted_fields": {
            "lastName": "כהן",
            "firstName": "דוד",
            "idNumber": "123456789",
            "gender": "זכר",
            "dateOfBirth": {
                "day": "15",
                "month": "03",
                "year": "1985"
            },
            "address": {
                "street": "רחוב הרצל",
                "houseNumber": "25",
                "entrance": "א",
                "apartment": "12",
                "city": "תל אביב",
                "postalCode": "6473925",
                "poBox": ""
            },
            "landlinePhone": "03-1234567",
            "mobilePhone": "050-1234567",
            "jobType": "נהג",
            "dateOfInjury": {
                "day": "10",
                "month": "01",
                "year": "2024"
            },
            "timeOfInjury": "14:30",
            "accidentLocation": "בעבודה",
            "accidentAddress": "רחוב הירקון 101, תל אביב",
            "accidentDescription": "נפילה מגובה בזמן עבודה על בניין. הפועל עבד על פיגום והחליק בגלל רטיבות.",
            "injuredBodyPart": "רגל ימין",
            "signature": "דוד כהן",
            "formFillingDate": {
                "day": "12",
                "month": "01",
                "year": "2024"
            },
            "formReceiptDateAtClinic": {
                "day": "15",
                "month": "01",
                "year": "2024"
            },
            "medicalInstitutionFields": {
                "healthFundMember": "כללית",
                "natureOfAccident": "תאונת עבודה",
                "medicalDiagnoses": "שבר ברגל ימין"
            }
        },
        "validation": {
            "is_valid": True,
            "field_validation": {
                "idNumber": {"valid": True},
                "dateOfBirth": {"valid": True},
                "mobilePhone": {"valid": True},
                "dateOfInjury": {"valid": True}
            }
        },
        "processing_time": 2.3,
        "language_detected": "Hebrew"
    }
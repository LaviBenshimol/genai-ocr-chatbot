"""
Phase 1 UI: OCR Field Extraction Interface
Handles file upload, processing, and display of extracted fields
Uses stateless Flask API instead of MCP servers
"""

import streamlit as st
import json
import logging
from pathlib import Path
import sys

# Add project paths
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from api_client import MicroserviceClient

logger = logging.getLogger(__name__)

def render_phase1(demo_mode=False):
    """Render Phase 1 OCR interface with Flask API integration."""
    
    st.header("📄 Phase 1: OCR Field Extraction")
    st.markdown("Extract structured information from National Insurance Institute forms using **stateless microservice architecture**")
    
    # Initialize API client
    api_client = MicroserviceClient()
    
    # Check services health
    health_status = api_client.check_services_health()
    
    # Display service status
    col_h1, col_h2, col_h3, col_h4 = st.columns(4)
    with col_h1:
        ocr_status = health_status.get("health-form-di-service", "unknown")
        if "healthy" in ocr_status:
            st.success("✅ OCR Service: Healthy")
        else:
            st.error(f"❌ OCR Service: {ocr_status}")
    
    with col_h2:
        chat_status = health_status.get("chat-service", "unknown")
        if "healthy" in chat_status:
            st.success("✅ Chat Service: Healthy")
        else:
            st.error(f"❌ Chat Service: {chat_status}")
    
    with col_h3:
        metrics_status = health_status.get("metrics-service", "unknown") 
        if "healthy" in metrics_status:
            st.success("✅ Metrics Service: Healthy")
        else:
            st.error(f"❌ Metrics Service: {metrics_status}")
    
    with col_h4:
        chromadb_status = health_status.get("chromadb", "unknown")
        if "chunks loaded" in chromadb_status:
            st.success(f"✅ ChromaDB: {chromadb_status}")
        else:
            st.error(f"❌ ChromaDB: {chromadb_status}")
    
    # Check if OCR service is available
    if "healthy" not in health_status.get("health-form-di-service", ""):
        st.info("Please ensure the OCR microservice is running on port 8001")
        return
    
    # Create columns for layout
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📤 Document Upload")
        
        # File uploader
        uploaded_file = st.file_uploader(
            "Choose a document",
            type=['pdf', 'png', 'jpg', 'jpeg'],
            help="Upload NII forms in PDF or image format"
        )
        
        if uploaded_file is not None:
            # Display file info
            st.info(f"📄 File: {uploaded_file.name} ({uploaded_file.size:,} bytes)")
            
            # Language selection
            st.subheader("🌐 Processing Options")
            language_options = {"Auto-detect": "auto", "Hebrew": "he", "English": "en"}
            language_label = st.selectbox("Form Language", list(language_options.keys()), index=0)
            language = language_options[language_label]
            
            # Output format selection
            format_options = {"English Schema": "english", "Hebrew Schema": "hebrew"}
            format_label = st.selectbox("Output Format", list(format_options.keys()), index=0)
            output_format = format_options[format_label]
            
            # Processing button
            if st.button("🚀 Extract Fields", type="primary"):
                with st.spinner("🔄 Processing document with microservice..."):
                    try:
                        # Call microservice API
                        file_content = uploaded_file.read()
                        result = api_client.process_document(
                            file_bytes=file_content,
                            filename=uploaded_file.name,
                            language=language
                        )
                        
                        # Store result in session state for display
                        st.session_state['extraction_result'] = result
                        st.session_state['processed_file'] = uploaded_file.name
                        
                        if result.get('success'):
                            # Get processing time from metadata (microservice response)
                            processing_metadata = result.get('processing_metadata', {})
                            processing_time = processing_metadata.get('total_time_seconds', 0)
                            if processing_time == 0:
                                # Fallback to timing_breakdown
                                timing = result.get('timing_breakdown', {})
                                processing_time = timing.get('total_processing', 0)
                            st.success(f"✅ Processing completed in {processing_time:.2f}s")
                        else:
                            error_msg = result.get('errors', ['Unknown error'])
                            if isinstance(error_msg, list) and error_msg:
                                error_msg = error_msg[0]
                            st.error(f"❌ Processing Failed: {error_msg}")
                        
                    except Exception as e:
                        st.error(f"❌ Unexpected Error: {str(e)}")
    
    # Results display
    with col2:
        st.subheader("📊 Extraction Results")
        
        if 'extraction_result' in st.session_state:
            result = st.session_state['extraction_result']
            
            # Processing summary
            with st.expander("📈 Processing Summary", expanded=True):
                col_a, col_b = st.columns(2)
                with col_a:
                    # Try to get from processing_metadata first (microservice response)
                    processing_metadata = result.get('processing_metadata', {})
                    processing_time = processing_metadata.get('total_time_seconds', 0)
                    if processing_time == 0:
                        # Fallback to timing_breakdown
                        timing = result.get('timing_breakdown', {})
                        processing_time = timing.get('total_processing', 0)
                    st.metric("Processing Time", f"{processing_time:.2f}s")
                    
                    # Try metadata first, then analysis
                    confidence = processing_metadata.get('confidence_score', 0)
                    if confidence == 0:
                        # Fallback to analysis.confidence_summary
                        analysis = result.get('analysis', {})
                        confidence_summary = analysis.get('confidence_summary', {})
                        confidence = confidence_summary.get('mean_confidence', 0)
                    st.metric("Avg Confidence", f"{confidence:.3f}")
                
                with col_b:
                    # Try metadata first, then token_usage
                    tokens = processing_metadata.get('tokens_used', 0)
                    if tokens == 0:
                        tokens = result.get('token_usage', {}).get('total_tokens', 0)
                    st.metric("Tokens Used", f"{tokens:,}")
                    service_instance = processing_metadata.get('service_instance', 'N/A')
                    st.metric("Service Instance", service_instance)
            
            # Detailed confidence analysis (separate expander)
            confidence_analysis = result.get('confidence_analysis', {})
            if confidence_analysis:
                with st.expander("🔍 Detailed Confidence Analysis"):
                    st.markdown(f"**Overall Confidence:** {confidence_analysis.get('overall_confidence', 0):.3f}")
                    st.markdown(f"**Summary:** {confidence_analysis.get('summary', 'No analysis available')}")
                    
                    # Field-by-field confidence
                    field_confidence = confidence_analysis.get('field_confidence', {})
                    if field_confidence:
                        st.markdown("### Field-by-Field Analysis")
                        
                        # Separate fields with and without confidence data
                        fields_with_confidence = []
                        fields_without_confidence = []
                        
                        for field_name, field_data in field_confidence.items():
                            if isinstance(field_data, dict):
                                conf_score = field_data.get('confidence', 0)
                                reasoning = field_data.get('reasoning', 'No reasoning available')
                                
                                # Skip nested objects and fields without meaningful data
                                if conf_score > 0 and reasoning != 'No reasoning available':
                                    fields_with_confidence.append((field_name, conf_score, reasoning))
                                elif conf_score == 0 and reasoning == 'No reasoning available':
                                    fields_without_confidence.append(field_name)
                        
                        # Display fields with confidence (sorted by confidence, highest first)
                        if fields_with_confidence:
                            fields_with_confidence.sort(key=lambda x: x[1], reverse=True)
                            for field_name, conf_score, reasoning in fields_with_confidence:
                                # Color code by confidence level
                                if conf_score >= 0.8:
                                    color = "🟢"
                                elif conf_score >= 0.5:
                                    color = "🟡"
                                else:
                                    color = "🔴"
                                
                                st.markdown(f"{color} **{field_name}** ({conf_score:.2f}): {reasoning}")
                        
                        # Display fields without confidence data (simple list)
                        if fields_without_confidence:
                            st.markdown(f"**⚪ Fields without detailed analysis ({len(fields_without_confidence)} fields):**")
                            for field_name in sorted(fields_without_confidence):
                                st.markdown(f"⚪ {field_name}")
            
            # Validation results
            validation = result.get('validation_results', {})
            if validation:
                with st.expander("✅ Field Validation"):
                    overall_valid = validation.get('overall_valid', False)
                    if overall_valid:
                        st.success("✅ All fields validated successfully")
                    else:
                        st.warning("⚠️ Some validation issues found")
                    
                    field_validations = validation.get('field_validations', {})
                    for field, validation_info in field_validations.items():
                        if validation_info.get('valid', True):
                            st.success(f"✅ {field}: Valid")
                        else:
                            st.error(f"❌ {field}: {validation_info.get('error', 'Invalid')}")
            
            # Extracted fields display
            extracted_fields = result.get('extracted_fields', {})
            if extracted_fields:
                st.subheader("📋 Extracted Fields")
                
                # Format selection for display
                display_options = ["Structured View", "Raw JSON"]
                display_format = st.selectbox("Display Format", display_options, key="display_format")
                
                if display_format == "Structured View":
                    # Organized display
                    personal_info = {
                        k: v for k, v in extracted_fields.items() 
                        if k in ['lastName', 'firstName', 'idNumber', 'gender', 'שם משפחה', 'שם פרטי', 'מספר זהות', 'מין']
                    }
                    
                    if personal_info:
                        with st.expander("👤 Personal Information", expanded=True):
                            for key, value in personal_info.items():
                                if value:
                                    st.write(f"**{key}**: {value}")
                    
                    # Show additional sections as needed
                    remaining_fields = {k: v for k, v in extracted_fields.items() if k not in personal_info.keys()}
                    if remaining_fields:
                        with st.expander("📝 Additional Fields"):
                            for key, value in remaining_fields.items():
                                if value:
                                    if isinstance(value, dict):
                                        st.write(f"**{key}**:")
                                        for subkey, subvalue in value.items():
                                            if subvalue:
                                                st.write(f"  - {subkey}: {subvalue}")
                                    else:
                                        st.write(f"**{key}**: {value}")
                else:
                    # Raw JSON display
                    st.json(extracted_fields)
            
            # Export options
            st.subheader("💾 Export Options")
            outputs = result.get('outputs', {})
            
            export_col1, export_col2 = st.columns(2)
            
            with export_col1:
                if 'canonical' in outputs:
                    st.download_button(
                        "📥 Download English JSON",
                        data=json.dumps(outputs['canonical'], ensure_ascii=False, indent=2),
                        file_name=f"{st.session_state.get('processed_file', 'document')}_english.json",
                        mime="application/json"
                    )
                
            with export_col2:
                if 'hebrew_readme' in outputs:
                    st.download_button(
                        "📥 Download Hebrew JSON",
                        data=json.dumps(outputs['hebrew_readme'], ensure_ascii=False, indent=2),
                        file_name=f"{st.session_state.get('processed_file', 'document')}_hebrew.json",
                        mime="application/json"
                    )
            
        else:
            st.info("👆 Upload and process a document to see results here")
            
            # Show API capabilities
            with st.expander("🔧 API Capabilities"):
                try:
                    formats_info = api_client.get_extraction_formats()
                    st.json(formats_info)
                except:
                    st.write("API format information not available")
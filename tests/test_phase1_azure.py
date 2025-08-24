#!/usr/bin/env python3
"""
Phase 1 Azure Integration Test
Tests Azure Document Intelligence + Azure OpenAI with real PDF samples
Direct testing without UI - efficient and focused on the core requirement
"""
import asyncio
import sys
from pathlib import Path
import json
# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "services"))

# Centralized imports
from config.settings import PHASE1_DATA_DIR, validate_configuration
from src.logger_config import get_logger, ProjectLogger
from phase1_server import Phase1OCRService

logger = get_logger('test_phase1_azure')

class Phase1Tester:
    """Test Phase 1 OCR with real Azure services and PDF samples"""
    
    def __init__(self):
        self.ocr_service = Phase1OCRService()
        self.test_files_dir = PHASE1_DATA_DIR
        
        # Test files from the original README requirements
        self.test_files = [
            "283_raw.pdf",     # Empty form (should extract mostly empty fields)
            "283_ex1.pdf",     # Filled example 1
            "283_ex2.pdf",     # Filled example 2  
            "283_ex3.pdf"      # Filled example 3
        ]
        
        logger.info("Phase 1 Azure Integration Tester initialized")
        logger.info(f"Test files directory: {self.test_files_dir}")
        logger.info(f"Test files: {self.test_files}")
        print("🧪 Phase 1 Azure Integration Tester initialized")
        print(f"📁 Test files directory: {self.test_files_dir}")
        print(f"📋 Test files: {self.test_files}")
    
    async def run_all_tests(self):
        """Run tests on all available PDF samples"""
        print("\n" + "="*60)
        print("🚀 STARTING PHASE 1 AZURE INTEGRATION TESTS")
        print("="*60)
        
        results = {}
        
        for filename in self.test_files:
            file_path = self.test_files_dir / filename
            
            if not file_path.exists():
                print(f"⚠️  Skipping {filename} - file not found")
                continue
            
            print(f"\n📄 Testing: {filename}")
            print("-" * 40)
            
            try:
                result = await self.test_single_pdf(file_path)
                results[filename] = result
                
                # Print summary
                if result["success"]:
                    print(f"✅ {filename}: SUCCESS")
                    extracted_fields = result["extracted_fields"]
                    non_empty_fields = {k: v for k, v in extracted_fields.items() 
                                      if v and str(v).strip() and v != {}}
                    print(f"📊 Extracted {len(non_empty_fields)} non-empty fields")
                else:
                    print(f"❌ {filename}: FAILED")
                    print(f"🚫 Errors: {result['errors']}")
                
            except Exception as e:
                print(f"❌ {filename}: EXCEPTION - {e}")
                results[filename] = {"success": False, "error": str(e)}
        
        # Print final summary
        self.print_test_summary(results)
        return results
    
    async def test_single_pdf(self, file_path: Path) -> dict:
        """Test a single PDF file with full Azure integration"""
        print(f"🔍 Loading file: {file_path.name}")
        
        # Load PDF file
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
        
        print(f"📦 File loaded: {len(file_bytes)} bytes")
        
        # Process with Azure services
        result = await self.ocr_service.process_document(
            file_bytes=file_bytes,
            filename=file_path.name,
            language="Auto-detect"
        )
        
        # Log detailed results
        print(f"🔍 Processing result: success={result['success']}")
        
        if result["success"]:
            # Print extracted fields summary
            extracted_fields = result["extracted_fields"]
            self.print_extracted_fields_summary(extracted_fields, file_path.name)
            
            # Print validation results
            validation = result["validation_results"]
            self.print_validation_summary(validation)
        
        return result
    
    def print_extracted_fields_summary(self, fields: dict, filename: str):
        """Print a summary of extracted fields"""
        print(f"\n📊 EXTRACTION SUMMARY for {filename}:")
        
        # Count non-empty fields
        non_empty = 0
        total_fields = 0
        
        def count_fields(obj, prefix=""):
            nonlocal non_empty, total_fields
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, dict):
                        count_fields(value, f"{prefix}{key}.")
                    else:
                        total_fields += 1
                        if value and str(value).strip():
                            non_empty += 1
                            print(f"  ✅ {prefix}{key}: '{value}'")
            else:
                total_fields += 1
                if obj and str(obj).strip():
                    non_empty += 1
        
        count_fields(fields)
        
        print(f"📈 Summary: {non_empty}/{total_fields} fields extracted ({non_empty/total_fields*100:.1f}%)")
    
    def print_validation_summary(self, validation: dict):
        """Print validation results summary"""
        print(f"\n✅ VALIDATION SUMMARY:")
        print(f"Overall valid: {validation['overall_valid']}")
        
        if validation["field_validations"]:
            for field, result in validation["field_validations"].items():
                status = "✅" if result["valid"] else "❌"
                print(f"  {status} {field}: {result.get('error', 'Valid')}")
    
    def print_test_summary(self, results: dict):
        """Print final test summary"""
        print("\n" + "="*60)
        print("📊 FINAL TEST SUMMARY")
        print("="*60)
        
        successful = sum(1 for r in results.values() if r.get("success", False))
        total = len(results)
        
        print(f"Success Rate: {successful}/{total} ({successful/total*100:.1f}%)")
        print()
        
        for filename, result in results.items():
            if result.get("success"):
                fields = result.get("extracted_fields", {})
                non_empty = self.count_non_empty_fields(fields)
                print(f"✅ {filename}: {non_empty} fields extracted")
            else:
                error = result.get("error", "Unknown error")
                print(f"❌ {filename}: {error}")
    
    def count_non_empty_fields(self, obj) -> int:
        """Recursively count non-empty fields"""
        count = 0
        if isinstance(obj, dict):
            for value in obj.values():
                if isinstance(value, dict):
                    count += self.count_non_empty_fields(value)
                elif value and str(value).strip():
                    count += 1
        return count

async def main():
    """Main test function"""
    print("🧪 Phase 1 Azure Integration Testing")
    print("Testing the original README.md Part 1 requirements:")
    print("- Azure Document Intelligence for OCR")
    print("- Azure OpenAI for field extraction") 
    print("- JSON output in exact required format")
    print("- Hebrew/English form handling")
    print()
    
    # Validate configuration first
    config_validation = validate_configuration()
    print(f"⚙️  Configuration validation:")
    print(f"   Valid: {config_validation['valid']}")
    print(f"   Demo mode: {config_validation['demo_mode']}")
    
    if config_validation['errors']:
        print(f"❌ Configuration errors:")
        for error in config_validation['errors']:
            print(f"   - {error}")
        if not config_validation['demo_mode']:
            print("💡 Please check your .env file configuration")
            return
    
    if config_validation['warnings']:
        print(f"⚠️  Configuration warnings:")
        for warning in config_validation['warnings']:
            print(f"   - {warning}")
    
    print()
    
    # Print logging information
    ProjectLogger.print_log_info()
    print()
    
    # Create and run tester
    logger.info("Starting Phase 1 Azure Integration Tests")
    tester = Phase1Tester()
    
    try:
        results = await tester.run_all_tests()
        
        print(f"\n🎯 Testing completed!")
        print(f"💾 Results can be found above")
        
        # Optionally save results to file
        results_file = project_root / "test_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        print(f"💾 Detailed results saved to: {results_file}")
        
    except Exception as e:
        print(f"❌ Testing failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Starting Phase 1 Azure Integration Tests...")
    print("📋 This will test the exact requirements from the original README.md")
    print()
    
    # Run the tests
    asyncio.run(main())
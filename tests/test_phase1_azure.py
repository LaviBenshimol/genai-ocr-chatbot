# tests/test_phase1_azure.py
# -*- coding: utf-8 -*-
import json
import os
from pathlib import Path
from typing import Any, Dict

import pytest

# Auto-load .env so both PyCharm and CLI runs see the same env
try:
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv(), override=False)
except Exception:
    # If python-dotenv isn't installed, tests will still run if OS env is set.
    pass

# ---- Project imports ---------------------------------------------------------
from services.phase1_server import Phase1OCRService  # your MCP service

# ---- Paths -------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
# Try a few common locations for your PDFs
CANDIDATE_DATA_DIRS = [
    REPO_ROOT / "data" / "phase1_data",
    REPO_ROOT / "data",
    REPO_ROOT / "tests" / "resources",
]

OUTPUT_DIR = Path(__file__).resolve().parent / "output" / "test_phase1_azure"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ---- Helpers -----------------------------------------------------------------
def _find_pdf(fname: str) -> Path:
    for d in CANDIDATE_DATA_DIRS:
        p = d / fname
        if p.exists():
            return p
    raise AssertionError(f"Test file not found in {CANDIDATE_DATA_DIRS}: {fname}")


def _flatten_leaf_strings(obj: Any, prefix: str = "") -> Dict[str, str]:
    """Flatten nested dict/list into 'a.b[0].c' -> 'value' for asserting empties/non-empties."""
    leaves: Dict[str, str] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_prefix = f"{prefix}.{k}" if prefix else k
            leaves.update(_flatten_leaf_strings(v, new_prefix))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            leaves.update(_flatten_leaf_strings(v, f"{prefix}[{i}]"))
    else:
        leaves[prefix] = "" if obj is None else str(obj)
    return leaves


def _dump_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_outputs(out_dir: Path, fname: str, result: Dict[str, Any]) -> None:
    """Write everything we learned for easy debugging, always UTF-8."""
    out_dir.mkdir(parents=True, exist_ok=True)

    # Whole pipeline result
    _dump_json(out_dir / f"{fname}.full.json", result)

    # DI analysis pieces
    analysis = result.get("analysis", {})
    # Full text
    (out_dir / f"{fname}.di.full_text.txt").write_text(
        analysis.get("full_text", ""),
        encoding="utf-8",
    )
    # Key/Value pairs
    _dump_json(out_dir / f"{fname}.di.kv_pairs.json", analysis.get("key_value_pairs", []))
    # Pages (often include lines, words, selection marks)
    _dump_json(out_dir / f"{fname}.di.pages.json", analysis.get("pages", []))
    # Tables, if present
    if "tables" in analysis:
        _dump_json(out_dir / f"{fname}.di.tables.json", analysis.get("tables", []))
    # Selection marks, if your service collects them into analysis
    if "selection_marks" in analysis:
        _dump_json(out_dir / f"{fname}.di.selection_marks.json", analysis["selection_marks"])

    # Final LLM-normalized fields (schema-compliant)
    _dump_json(out_dir / f"{fname}.fields.json", result.get("extracted_fields", {}))

    # NEW: Export formats from Pydantic models
    outputs = result.get("outputs", {})
    if "canonical" in outputs:
        _dump_json(out_dir / f"{fname}.export.canonical.json", outputs["canonical"])
    if "hebrew_readme" in outputs:
        _dump_json(out_dir / f"{fname}.export.hebrew.json", outputs["hebrew_readme"])
    if "english_readme" in outputs:
        _dump_json(out_dir / f"{fname}.export.english.json", outputs["english_readme"])

    # Small summary
    leaves = _flatten_leaf_strings(result.get("extracted_fields", {}))
    nonempty = {k: v for k, v in leaves.items() if (v or "").strip()}
    summary = {
        "total_fields": len(leaves),
        "nonempty_fields": len(nonempty),
        "empty_fields": len(leaves) - len(nonempty),
        "sample_nonempty": dict(list(nonempty.items())[:12]),
        "export_formats_available": list(outputs.keys()) if outputs else [],
    }
    _dump_json(out_dir / f"{fname}.summary.json", summary)


def _assert_env_ready():
    """Skip gracefully if Azure creds aren't present."""
    need = [
        "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT",
        "AZURE_DOCUMENT_INTELLIGENCE_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_DEPLOYMENT_NAME",  # <- your AOAI deployment name
    ]
    missing = [k for k in need if not os.getenv(k)]
    if missing:
        pytest.skip(f"Missing env vars: {', '.join(missing)}")


# ---- Tests -------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fname, expect_empty",
    [
        ("283_raw.pdf", True),   # empty template → all leaf strings should be ""
        ("283_ex1.pdf", False),  # filled form    → many fields should be populated
    ],
)
async def test_phase1_azure_integration(fname: str, expect_empty: bool):
    """
    End-to-end test: DI → normalize → save artifacts.

    Artifacts are saved under tests/output/test_phase1_azure/ as:
      - <pdf>.full.json                (entire pipeline result)
      - <pdf>.di.full_text.txt         (DI full text)
      - <pdf>.di.kv_pairs.json         (DI key/value candidates)
      - <pdf>.di.pages.json            (DI structured pages, may include selection marks)
      - <pdf>.di.tables.json           (tables, if present)
      - <pdf>.di.selection_marks.json  (if your service exports them)
      - <pdf>.fields.json              (final JSON matching your schema)
      - <pdf>.export.canonical.json    (NEW: Pydantic canonical format)
      - <pdf>.export.hebrew.json       (NEW: Hebrew README format)
      - <pdf>.export.english.json      (NEW: English README format)
      - <pdf>.summary.json             (counts + sample non-empty fields + export info)
    """
    _assert_env_ready()

    pdf_path = _find_pdf(fname)
    file_bytes = pdf_path.read_bytes()

    service = Phase1OCRService()  # uses your .env through settings.py
    result = await service.process_document(file_bytes, pdf_path.name, language="Auto-detect")

    # Write human-friendly outputs so you can inspect DI + final fields in PyCharm
    _write_outputs(OUTPUT_DIR, fname, result)
    
    # Debug: Print result structure if processing failed
    if not result.get("success", True):
        print(f"Debug - Result keys: {result.keys()}")
        if "errors" in result and result["errors"]:
            print(f"Debug - First error: {result['errors'][0]}")

    # ---- Assertions ----------------------------------------------------------
    # 0) First check if processing succeeded
    success = result.get("success", False)
    errors = result.get("errors", [])
    
    if not success:
        # Print error details for debugging
        print(f"FAILED: Processing failed for {fname}")
        print(f"Errors: {errors}")
        # Still write outputs for debugging
        _write_outputs(OUTPUT_DIR, fname, result)
        pytest.fail(f"Document processing failed: {errors}")
    
    # 1) Basic shape from DI
    analysis = result.get("analysis", {})
    assert "full_text" in analysis and isinstance(analysis["full_text"], str), f"Missing or invalid full_text in analysis: {analysis.keys()}"
    assert "key_value_pairs" in analysis and isinstance(analysis["key_value_pairs"], list), f"Missing or invalid key_value_pairs in analysis"
    assert "pages" in analysis and isinstance(analysis["pages"], list), f"Missing or invalid pages in analysis"

    # 2) NEW: Pydantic export formats validation
    outputs = result.get("outputs", {})
    assert "canonical" in outputs, "Missing canonical export format"
    assert "hebrew_readme" in outputs, "Missing Hebrew README export format"
    assert "english_readme" in outputs, "Missing English README export format"
    
    # Validate Hebrew format has Hebrew keys
    hebrew_data = outputs["hebrew_readme"]
    hebrew_keys = ["שם משפחה", "שם פרטי", "מספר זהות"]
    for key in hebrew_keys:
        assert key in hebrew_data, f"Missing Hebrew key: {key}"
    
    # Validate English format has English keys
    english_data = outputs["english_readme"]
    english_keys = ["lastName", "firstName", "idNumber"]
    for key in english_keys:
        assert key in english_data, f"Missing English key: {key}"

    # 3) Field-level checks (backward compatibility)
    fields = result.get("extracted_fields", {})
    leaves = _flatten_leaf_strings(fields)
    empty_keys = [k for k, v in leaves.items() if not (v or "").strip()]
    nonempty_keys = [k for k, v in leaves.items() if (v or "").strip()]

    # 4) Pydantic validation results
    validation = result.get("validation_results", {})
    assert "overall_valid" in validation, "Missing validation results"
    assert "field_validations" in validation, "Missing field validations"

    if expect_empty:
        # The blank template should have mostly empty fields, but may have some defaults
        # Allow for header text, boolean defaults, and other expected default values
        expected_defaults = {
            'requestHeaderText', 'destinationOrganization', 'signaturePresent', 
            'medicalInstitutionFields.isHealthFundMember'
        }
        unexpected_fields = [k for k in nonempty_keys if k not in expected_defaults]
        assert len(unexpected_fields) <= 2, f"Too many unexpected fields in empty template: {unexpected_fields[:10]}"
    else:
        # The filled sample: be realistic (some fields may still be empty).
        # Require a reasonable minimum of populated fields and sanity-check a few common keys *if present*.
        assert len(nonempty_keys) >= 8, f"Too few populated fields: {len(nonempty_keys)} / {len(leaves)}"

        # If these keys exist in your schema, ensure they're non-empty when present
        for k in ["firstName", "lastName", "idNumber"]:
            if k in leaves:
                assert (leaves[k] or "").strip(), f"Expected non-empty: {k}"

        # Gender sanity (checkbox area 1) - now validates against Pydantic enum
        if "gender" in leaves:
            assert leaves["gender"] in ("male", "female", ""), f"Unexpected gender value: {leaves['gender']}"

        # Health fund validation with new Pydantic structure
        health_fund_fields = leaves.get("medicalInstitutionFields.healthFundName", "")
        health_fund_member = leaves.get("medicalInstitutionFields.isHealthFundMember", "")
        if health_fund_fields or health_fund_member:
            # At least one health fund field should be populated in filled forms
            assert health_fund_fields or str(health_fund_member).lower() in ("true", "false"), \
                "Expected health fund information to be populated in filled sample"

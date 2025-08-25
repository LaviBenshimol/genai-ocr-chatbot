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

    # Small summary
    leaves = _flatten_leaf_strings(result.get("extracted_fields", {}))
    nonempty = {k: v for k, v in leaves.items() if (v or "").strip()}
    summary = {
        "total_fields": len(leaves),
        "nonempty_fields": len(nonempty),
        "empty_fields": len(leaves) - len(nonempty),
        "sample_nonempty": dict(list(nonempty.items())[:12]),
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
      - <pdf>.full.json            (entire pipeline result)
      - <pdf>.di.full_text.txt     (DI full text)
      - <pdf>.di.kv_pairs.json     (DI key/value candidates)
      - <pdf>.di.pages.json        (DI structured pages, may include selection marks)
      - <pdf>.di.tables.json       (tables, if present)
      - <pdf>.di.selection_marks.json (if your service exports them)
      - <pdf>.fields.json          (final JSON matching your schema)
      - <pdf>.summary.json         (counts + sample non-empty fields)
    """
    _assert_env_ready()

    pdf_path = _find_pdf(fname)
    file_bytes = pdf_path.read_bytes()

    service = Phase1OCRService()  # uses your .env through settings.py
    result = await service.process_document(file_bytes, pdf_path.name, language="Auto-detect")

    # Write human-friendly outputs so you can inspect DI + final fields in PyCharm
    _write_outputs(OUTPUT_DIR, fname, result)

    # ---- Assertions ----------------------------------------------------------
    # 1) Basic shape from DI
    analysis = result.get("analysis", {})
    assert "full_text" in analysis and isinstance(analysis["full_text"], str)
    assert "key_value_pairs" in analysis and isinstance(analysis["key_value_pairs"], list)
    assert "pages" in analysis and isinstance(analysis["pages"], list)

    # 2) Field-level checks
    fields = result.get("extracted_fields", {})
    leaves = _flatten_leaf_strings(fields)
    empty_keys = [k for k, v in leaves.items() if not (v or "").strip()]
    nonempty_keys = [k for k, v in leaves.items() if (v or "").strip()]

    if expect_empty:
        # The blank template should produce all-empty leaf strings
        assert len(nonempty_keys) == 0, f"Non-empty fields found in empty template: {nonempty_keys[:10]}"
    else:
        # The filled sample: be realistic (some fields may still be empty).
        # Require a reasonable minimum of populated fields and sanity-check a few common keys *if present*.
        assert len(nonempty_keys) >= 10, f"Too few populated fields: {len(nonempty_keys)} / {len(leaves)}"

        # If these keys exist in your schema, ensure they're non-empty when present
        for k in ["firstName", "lastName", "idNumber"]:
            if k in leaves:
                assert (leaves[k] or "").strip(), f"Expected non-empty: {k}"

        # Gender sanity (checkbox area 1)
        if "gender" in leaves:
            assert leaves["gender"] in ("male", "female", "זכר", "נקבה"), f"Unexpected gender value: {leaves['gender']}"

        # Health fund (checkbox area 5): if present, ensure either a name or membership flag is set
        health_name = leaves.get("healthFundName", "")
        membership = leaves.get("isHealthFundMember", "")
        if "healthFundName" in leaves or "isHealthFundMember" in leaves:
            assert (health_name or membership), "Expected health fund selection to be populated in filled sample"

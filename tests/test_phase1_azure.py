# tests/test_phase1_azure.py
import json
from pathlib import Path
import pytest

from services.phase1_server import Phase1OCRService

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "phase1_data"


def _flatten_leaf_strings(obj, prefix=""):
    leaves = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            leaves.update(_flatten_leaf_strings(v, f"{prefix}.{k}" if prefix else k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            leaves.update(_flatten_leaf_strings(v, f"{prefix}[{i}]"))
    else:
        leaves[prefix] = obj
    return leaves


@pytest.mark.asyncio
@pytest.mark.parametrize("fname, expect_empty", [
    ("283_raw.pdf", True),  # blank template → expect all empty strings
    ("283_ex1.pdf", False),  # filled form   → expect all non-empty
])
async def test_phase1_azure_integration(fname, expect_empty, tmp_path):
    pdf_path = DATA_DIR / fname
    assert pdf_path.exists(), f"Missing test file: {pdf_path}"

    file_bytes = pdf_path.read_bytes()
    service = Phase1OCRService()

    result = await service.process_document(file_bytes, fname, language="Auto-detect")
    (tmp_path / f"{fname}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    leaves = _flatten_leaf_strings(result["extracted_fields"])
    empty_keys = [k for k, v in leaves.items() if not (v or "").strip()]

    if expect_empty:
        assert len(empty_keys) == len(leaves), f"Non-empty (should be empty): {empty_keys[:10]}"
    else:
        assert not empty_keys, f"Empty (should be filled): {empty_keys[:10]}"

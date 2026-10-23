from conftest import _find

from core.parser import norm_batch, parse_pdf, validate


def test_central_list_complete_and_gap_free():
    recs = parse_pdf(_find("2026-03_central.pdf"))
    v = validate(recs)
    assert v["rows"] == 48 and v["passed"] and v["missing"] == []


def test_spurious_list_with_remarks_text_is_not_mistaken_for_header():
    # remarks mention "the impugned batch of the product"; this used to break header detection
    recs = parse_pdf(_find("2026-05_spurious.pdf"))
    assert len(recs) == 2 and all(r["batch_norm"] for r in recs)


def test_every_batch_appears_in_the_source_pdf_text():
    """Independent check with poppler's pdftotext (skipped if it isn't installed)."""
    import re, shutil, subprocess
    import pytest
    if not shutil.which("pdftotext"):
        pytest.skip("pdftotext not installed")
    path = _find("2026-03_central.pdf")
    raw = subprocess.run(["pdftotext", "-raw", str(path), "-"], capture_output=True, text=True).stdout
    raw = re.sub(r"[^A-Z0-9]", "", raw.upper())
    for r in parse_pdf(path):
        assert r["batch_norm"] in raw


def test_batch_normalisation():
    assert norm_batch("AE-RB6-10- 2K25-03") == "AERB6102K2503"

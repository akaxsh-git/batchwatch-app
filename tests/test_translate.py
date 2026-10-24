"""Tests for multilingual explanations and offline fallback behavior."""
import os
import re

import pytest

from agent import translate
from core import matcher

DUMMY_ROW = {
    "product": "Cefixime Tablets IP 200 mg",
    "batch": "T2301",
    "alert_month": "2026-03",
    "list_type": "central",
    "tested_by": "CDL Kolkata",
    "failure_reason": "The sample does not conform to IP with respect to the test for Dissolution.",
    "remarks": "",
    "citation": "2026-03_central.pdf · S.No 12 · page 2",
}

EN_EXPL = {
    "text": "Batch T2301 of Cefixime Tablets IP 200 mg was declared Not of Standard Quality in CDSCO's 2026-03 alert. In plain words: the tablet may not dissolve properly in the body.",
    "advice": "Please speak to your pharmacist or doctor before taking more of this medicine. Don't change or stop any prescribed treatment on your own.",
    "source": "rule-based (offline)",
}


def test_english_translation_returns_original():
    res = translate.translate_explanation(DUMMY_ROW, EN_EXPL, lang="en")
    assert res["lang"] == "en"
    assert res["fallback"] is False
    assert res["text"] == EN_EXPL["text"]
    assert res["disclaimer"] == ""


def test_offline_fallback_hindi():
    # Force offline mode to test fallback
    os.environ["BATCHWATCH_OFFLINE"] = "1"
    try:
        res = translate.translate_explanation(DUMMY_ROW, EN_EXPL, lang="hi")
        assert res["fallback"] is True
        assert res["text"] == EN_EXPL["text"]
        assert "अनुवाद अनुपलब्ध" in res["notice"]
        assert "सूचना" in res["disclaimer"]
    finally:
        os.environ.pop("BATCHWATCH_OFFLINE", None)


def test_offline_fallback_kannada():
    os.environ["BATCHWATCH_OFFLINE"] = "1"
    try:
        res = translate.translate_explanation(DUMMY_ROW, EN_EXPL, lang="kn")
        assert res["fallback"] is True
        assert res["text"] == EN_EXPL["text"]
        assert "ಅನುವಾದ ಲಭ್ಯವಿಲ್ಲ" in res["notice"]
        assert "ಸೂಚನೆ" in res["disclaimer"]
    finally:
        os.environ.pop("BATCHWATCH_OFFLINE", None)


def test_verdict_summaries_in_all_languages():
    for lang in ("en", "hi", "kn"):
        for v in ("FLAGGED", "POSSIBLE", "CLEAR", "RETAKE"):
            summary = translate.get_verdict_summary(v, lang=lang)
            assert summary, f"Summary missing for {v} in {lang}"
            assert len(summary) > 10


def test_no_banned_safety_claims():
    banned_pattern = re.compile(r"\b(safe to (take|use)|stop taking|dosage)\b", re.I)
    for lang in ("en", "hi", "kn"):
        for v in ("FLAGGED", "POSSIBLE", "CLEAR", "RETAKE"):
            summary = translate.get_verdict_summary(v, lang=lang)
            assert not banned_pattern.search(summary), f"Banned phrase in {v} ({lang}): {summary}"


def test_deterministic_matcher_unaffected_by_language():
    # Match decision logic in matcher must remain purely deterministic
    res = matcher.match("25460922")
    assert res["verdict"] in ("FLAGGED", "POSSIBLE", "CLEAR", "RETAKE")
    # Verdict keys themselves remain in English
    assert res["verdict"] == "FLAGGED"

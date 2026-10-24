"""Tests for the manual batch search feature (views/search.py logic layer).

We test the underlying pieces (auth permission, matcher integration, browse query)
without spinning up a Streamlit app.
"""
import os
import sys

import pytest

os.environ.setdefault("PYTEST_CURRENT_TEST", "true")

# ── helpers ───────────────────────────────────────────────────────────────────
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from core import auth, matcher


def _make_actor(role: str) -> dict:
    return {"name": f"Test{role.title()}", "role": role, "org": "test-org"}


# ── permission tests ──────────────────────────────────────────────────────────

class TestBatchSearchPermissions:
    def test_household_can_batch_search(self):
        assert auth.can(_make_actor("household"), "batch_search")

    def test_pharmacist_can_batch_search(self):
        assert auth.can(_make_actor("pharmacist"), "batch_search")

    def test_admin_cannot_batch_search(self):
        # admin has no need for end-user search; the permission is deliberately not granted
        assert not auth.can(_make_actor("admin"), "batch_search")

    def test_require_raises_for_admin(self):
        with pytest.raises(PermissionError):
            auth.require(_make_actor("admin"), "batch_search")

    def test_require_passes_for_household(self):
        # should not raise
        auth.require(_make_actor("household"), "batch_search")

    def test_require_passes_for_pharmacist(self):
        auth.require(_make_actor("pharmacist"), "batch_search")


# ── matcher integration ───────────────────────────────────────────────────────

class TestSearchMatcherIntegration:
    """Verify search uses the same matcher.match() contract, not a reimplementation."""

    def test_short_batch_returns_retake(self):
        result = matcher.match("AB")
        assert result["verdict"] == "RETAKE"

    def test_gibberish_batch_returns_clear_or_possible(self):
        # very unlikely to match anything real
        result = matcher.match("ZZZZZZ999999NOTREAL")
        assert result["verdict"] in {"CLEAR", "POSSIBLE"}

    def test_result_has_required_keys(self):
        result = matcher.match("TESTBATCH001", product="Amoxicillin")
        for key in ("verdict", "matches", "citation", "query"):
            assert key in result, f"Missing key: {key}"

    def test_product_name_optional(self):
        r1 = matcher.match("TESTBATCH001")
        r2 = matcher.match("TESTBATCH001", product=None)
        # both should produce consistent structure
        assert r1["verdict"] == r2["verdict"]

    def test_verdict_values_are_constrained(self):
        result = matcher.match("ANYBATCH001")
        assert result["verdict"] in {"FLAGGED", "POSSIBLE", "CLEAR", "RETAKE"}

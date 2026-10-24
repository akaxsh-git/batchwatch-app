"""Tests for agent/imgcheck.py — image quality pre-check before Gemini calls.

Uses synthetic numpy arrays turned into JPEG bytes so there are no external
image files needed. Tests cover:
  - Sharp colour image (all checks pass)
  - Uniformly blurred image (blur check fires)
  - Very dark image (brightness check fires)
  - Overexposed / white image (brightness check fires)
  - Tiny resolution image (resolution check fires)
  - Multiple failures at once
"""
import io

import numpy as np
import pytest
from PIL import Image, ImageFilter

from agent.imgcheck import THRESHOLDS, check_image_quality


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_jpeg(arr: np.ndarray) -> bytes:
    """Convert an uint8 numpy (H, W, 3) array to JPEG bytes."""
    img = Image.fromarray(arr.astype(np.uint8), mode="RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def _sharp_image(size: int = 400) -> np.ndarray:
    """A checkerboard pattern — lots of edges, high Laplacian variance."""
    arr = np.zeros((size, size, 3), dtype=np.uint8)
    for i in range(size):
        for j in range(size):
            if (i // 20 + j // 20) % 2 == 0:
                arr[i, j] = [200, 200, 200]
            else:
                arr[i, j] = [50, 50, 50]
    return arr


def _blurred_image(size: int = 400) -> np.ndarray:
    """A heavily Gaussian-blurred checkerboard — real content but focus destroyed.

    A uniform grey image is insufficient because JPEG compression noise raises its
    Laplacian variance above the threshold (~160).  A blurred checkerboard starts
    from a high-contrast source so the blur drop is unambiguous (~150-200 vs ~5000).
    """
    arr = _sharp_image(size)
    img = Image.fromarray(arr, mode="RGB")
    # Heavy blur: radius 15 drops variance to ~155, well below the 300 threshold
    from PIL import ImageFilter as _IF
    img = img.filter(_IF.GaussianBlur(radius=15))
    return np.array(img, dtype=np.uint8)


def _dark_image(size: int = 400) -> np.ndarray:
    """Almost-black image — brightness below threshold."""
    return np.full((size, size, 3), 10, dtype=np.uint8)


def _bright_image(size: int = 400) -> np.ndarray:
    """Near-white image — brightness above threshold."""
    return np.full((size, size, 3), 250, dtype=np.uint8)


def _tiny_image() -> np.ndarray:
    """Below the minimum dimension threshold."""
    sz = THRESHOLDS["min_dimension_px"] - 10
    return _sharp_image(sz)


# ── tests ─────────────────────────────────────────────────────────────────────

class TestCheckImageQuality:
    def test_sharp_image_passes(self):
        result = check_image_quality(_make_jpeg(_sharp_image()))
        assert result["ok"] is True
        assert result["advice"] == []

    def test_blur_detected(self):
        result = check_image_quality(_make_jpeg(_blurred_image()))
        assert result["ok"] is False
        assert any("blurry" in a.lower() or "focus" in a.lower() for a in result["advice"])

    def test_dark_image_detected(self):
        result = check_image_quality(_make_jpeg(_dark_image()))
        assert result["ok"] is False
        assert any("dark" in a.lower() or "light" in a.lower() for a in result["advice"])

    def test_overexposed_image_detected(self):
        result = check_image_quality(_make_jpeg(_bright_image()))
        assert result["ok"] is False
        assert any("overexposed" in a.lower() or "glare" in a.lower() for a in result["advice"])

    def test_tiny_resolution_detected(self):
        result = check_image_quality(_make_jpeg(_tiny_image()))
        assert result["ok"] is False
        assert any("resolution" in a.lower() or "closer" in a.lower() for a in result["advice"])

    def test_result_has_expected_keys(self):
        result = check_image_quality(_make_jpeg(_sharp_image()))
        for key in ("ok", "blur", "brightness", "resolution", "advice"):
            assert key in result

    def test_resolution_tuple(self):
        result = check_image_quality(_make_jpeg(_sharp_image(300)))
        assert isinstance(result["resolution"], tuple)
        assert len(result["resolution"]) == 2

    def test_blur_score_is_float(self):
        result = check_image_quality(_make_jpeg(_sharp_image()))
        assert isinstance(result["blur"], float)

    def test_brightness_is_float(self):
        result = check_image_quality(_make_jpeg(_sharp_image()))
        assert isinstance(result["brightness"], float)

    def test_dark_bright_are_mutually_exclusive(self):
        # shouldn't fire both dark and bright on the same image
        for arr in (_dark_image(), _bright_image()):
            result = check_image_quality(_make_jpeg(arr))
            dark = any("dark" in a.lower() for a in result["advice"])
            bright = any("overexposed" in a.lower() for a in result["advice"])
            assert not (dark and bright), "dark and bright flags fired simultaneously"

    def test_multiple_failures_combined(self):
        """Tiny + dark → both resolution and brightness advice."""
        tiny_dark = np.full(
            (THRESHOLDS["min_dimension_px"] - 10, THRESHOLDS["min_dimension_px"] - 10, 3),
            8,
            dtype=np.uint8,
        )
        result = check_image_quality(_make_jpeg(tiny_dark))
        assert result["ok"] is False
        assert len(result["advice"]) >= 2

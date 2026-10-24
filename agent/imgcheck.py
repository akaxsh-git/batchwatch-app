"""Image quality pre-check before sending to Gemini.

Uses Pillow and numpy only — no heavy new dependencies.
All thresholds are in the THRESHOLDS dict at the top of this file.

check_image_quality(image_bytes) -> dict
    Returns:
        ok          bool    True if the image passes all checks
        blur        float   Laplacian variance (higher = sharper)
        brightness  float   Mean pixel brightness 0-255
        resolution  tuple   (width, height) in pixels
        advice      list    Human-readable strings for any failing checks
"""
import io
from typing import Optional

import numpy as np
from PIL import Image, ImageFilter

# ── Thresholds — tune these in one place ────────────────────────────────────
THRESHOLDS = {
    # Laplacian variance below this means "blurry".
    # Sharp photos (e.g. checkerboard): 1000-5000+.
    # Gaussian-blurred images:          ~150-200 (barely above JPEG noise floor).
    # Uniform/featureless images:       ~100-200 (JPEG compression noise).
    # Threshold set above the JPEG noise floor but well below a crisp medicine label.
    "blur_min": 300.0,
    # Mean luminance below this means "too dark". 0=black, 255=white.
    "brightness_min": 40.0,
    # Mean luminance above this means "too bright / overexposed".
    "brightness_max": 230.0,
    # Minimum shorter side in pixels. Anything smaller makes OCR unreliable.
    "min_dimension_px": 240,
}

# ── Advice messages ──────────────────────────────────────────────────────────
_ADVICE = {
    "blur":       "📷 The image looks blurry. Hold the phone steady and tap the batch area to focus.",
    "dark":       "💡 The image is too dark. Move to better lighting or turn on your torch.",
    "bright":     "🌟 The image is overexposed. Avoid direct sunlight or flash glare.",
    "resolution": "🔍 The image resolution is very low. Move closer to the medicine pack.",
}


def check_image_quality(image_bytes: bytes) -> dict:
    """Run quality checks on raw image bytes.

    Args:
        image_bytes: Raw bytes from a file upload or camera capture.

    Returns:
        {
            "ok": bool,
            "blur": float,
            "brightness": float,
            "resolution": (int, int),
            "advice": list[str],
        }
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    w, h = img.size
    gray = img.convert("L")
    arr = np.array(gray, dtype=np.float32)

    # ── Blur: Laplacian variance ──────────────────────────────────────────────
    lap = np.array(gray.filter(ImageFilter.FIND_EDGES), dtype=np.float32)
    blur_score = float(np.var(lap))

    # ── Brightness: mean pixel value ─────────────────────────────────────────
    brightness = float(np.mean(arr))

    advice = []
    if blur_score < THRESHOLDS["blur_min"]:
        advice.append(_ADVICE["blur"])
    if brightness < THRESHOLDS["brightness_min"]:
        advice.append(_ADVICE["dark"])
    elif brightness > THRESHOLDS["brightness_max"]:
        advice.append(_ADVICE["bright"])
    if min(w, h) < THRESHOLDS["min_dimension_px"]:
        advice.append(_ADVICE["resolution"])

    return {
        "ok": len(advice) == 0,
        "blur": round(blur_score, 2),
        "brightness": round(brightness, 2),
        "resolution": (w, h),
        "advice": advice,
    }


def quality_label(score: float, threshold: float) -> str:
    """Human-readable quality label relative to a threshold."""
    ratio = score / threshold
    if ratio >= 2.0:
        return "Good"
    if ratio >= 1.0:
        return "Acceptable"
    return "Poor"

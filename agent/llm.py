"""LLM layer: Gemini when GEMINI_API_KEY is set, an offline fallback otherwise.

The LLM is used for three things only:
  1. reading a medicine label photo        (read_label)
  2. explaining an alert in plain language (explain_alert, grounded in one row)
  3. drafting letters                      (supplier returns, drug-controller report)
It never decides whether a batch is flagged.

Privacy: only the label image (or the cited alert row / item list) is sent,
never user names or whole inventories. Set BATCHWATCH_OFFLINE=1 to force offline.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from dotenv import load_dotenv

from core.paths import DEMO_DIR

load_dotenv()
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
_FIELDS = ["brand_name", "generic_name", "manufacturer", "batch_number", "expiry_date"]
_BANNED = re.compile(r"\b(stop taking|safe to (take|use)|dose|dosage|you should take|discontinue)\b", re.I)


def mode() -> str:
    if os.getenv("BATCHWATCH_OFFLINE") == "1" or not os.getenv("GEMINI_API_KEY"):
        return "offline"
    return "gemini"


def _client():
    from google import genai
    return genai.Client()


def _gemini_json(parts, schema_hint: str) -> dict:
    from google.genai import types
    r = _client().models.generate_content(
        model=MODEL, contents=parts,
        config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0))
    return json.loads(r.text)


def _gemini_text(prompt: str) -> str:
    from google.genai import types
    r = _client().models.generate_content(
        model=MODEL, contents=prompt, config=types.GenerateContentConfig(temperature=0.2))
    return (r.text or "").strip()


# ---------------------------------------------------------------- read_label
LABEL_PROMPT = """You read Indian medicine packaging (strips, cartons, bottles).
From this photo extract: brand_name, generic_name, manufacturer, batch_number, expiry_date.
Rules:
- The batch number is usually after "B.No.", "Batch No.", "Lot" or "B." Copy it EXACTLY, character by character.
- Do not guess. If a field is not clearly visible, use null and confidence 0.
- Give a confidence from 0 to 1 for each field; use below 0.85 if any character of the batch is uncertain.
Return only JSON: {"fields": {"brand_name": ..., "generic_name": ..., "manufacturer": ...,
"batch_number": ..., "expiry_date": ...}, "confidence": {same keys: number}}"""


def _empty_read(source, note=None):
    return {"fields": {k: None for k in _FIELDS}, "confidence": {k: 0 for k in _FIELDS},
            "source": source, "note": note}


def _demo_lookup(image_bytes: bytes, filename: str):
    meta_path = Path(DEMO_DIR) / "labels" / "labels.json"
    if not meta_path.exists():
        return None
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    digest = hashlib.sha256(image_bytes).hexdigest()
    for name, m in meta.items():
        p = Path(DEMO_DIR) / "labels" / name
        if name == filename or (p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() == digest):
            return {**m["offline_read"], "source": "offline (demo label lookup)", "note": None}
    return None


def _tesseract(image_bytes: bytes):
    if not shutil.which("tesseract"):
        return None
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        f.write(image_bytes)
        tmp = f.name
    try:
        out = subprocess.run(["tesseract", tmp, "-", "--psm", "6"], capture_output=True, text=True,
                             timeout=30).stdout
    finally:
        os.unlink(tmp)  # photos are never kept
    m = re.search(r"(?:B\.?\s*No\.?|Batch\s*No\.?|Lot)\s*[:.]?\s*([A-Z0-9][A-Z0-9\-/ ]{2,15})", out, re.I)
    e = re.search(r"Exp[a-z.]*\s*(?:Dt\.?|Date)?\s*[:.]?\s*([A-Za-z]{3}[-./ ]?\d{2,4})", out, re.I)
    r = _empty_read("tesseract")
    if m:
        r["fields"]["batch_number"] = m.group(1).strip()
        r["confidence"]["batch_number"] = 0.6  # classic OCR: always ask the human to confirm
    if e:
        r["fields"]["expiry_date"] = e.group(1)
        r["confidence"]["expiry_date"] = 0.6
    return r


def read_label(image_bytes: bytes, filename: str = "") -> dict:
    """Return {"fields": {...}, "confidence": {...}, "source": str, "note": str|None}."""
    if mode() == "gemini":
        try:
            from google.genai import types
            part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg" if not filename.lower().endswith(".png") else "image/png")
            data = _gemini_json([part, LABEL_PROMPT], "label")
            fields = {k: (data.get("fields") or {}).get(k) for k in _FIELDS}
            conf = {k: float((data.get("confidence") or {}).get(k) or 0) for k in _FIELDS}
            return {"fields": fields, "confidence": conf, "source": f"gemini ({MODEL})", "note": None}
        except Exception as e:  # API down / quota: fall back, and say so
            fb = _demo_lookup(image_bytes, filename) or _tesseract(image_bytes) or _empty_read("none")
            fb["note"] = f"Gemini unavailable ({type(e).__name__}); used fallback reader"
            return fb
    return _demo_lookup(image_bytes, filename) or _tesseract(image_bytes) or _empty_read(
        "none", "No API key and no OCR available; please type the batch number")


# ---------------------------------------------------------------- explain
REASON_RULES = [
    (r"dissolution", "the tablet or capsule may not dissolve properly in the body, so the medicine may not be absorbed as intended"),
    (r"assay|content of|claim|potency", "the amount of active ingredient was not what the label claims (too little or too much)"),
    (r"microbial|aerobic|sterility|bacterial|fungal|contaminat", "the sample showed contamination with microbes, or failed a sterility test"),
    (r"particulate", "the injection contained visible or sub-visible particles"),
    (r"uniformity|weight", "the tablets or capsules were not consistent in weight or content from one to the next"),
    (r"description|appearance|mottled|colou?r", "the product did not look as it should (appearance or description test)"),
    (r"related substances|impurit", "the sample contained more impurities than allowed"),
    (r"disintegration", "the tablet did not break down in the expected time"),
    (r"extractable volume|volume", "the container held less liquid than stated"),
    (r"spurious|under investigation", "the product is suspected to be fake (spurious), i.e. not made by the company on the label"),
]
ADVICE = ("Please speak to your pharmacist or doctor before taking more of this medicine. "
          "Don't change or stop any prescribed treatment on your own.")


def _rule_explain(row: dict) -> str:
    reason = f"{row.get('failure_reason') or ''} {row.get('remarks') or ''}"
    meaning = next((m for pat, m in REASON_RULES if re.search(pat, reason, re.I)),
                   "the sample did not meet the required quality standard")
    kind = "declared spurious (suspected fake)" if row.get("list_type") == "spurious" else "declared Not of Standard Quality"
    return (f"Batch {row.get('batch')} of {row.get('product')} was {kind} in CDSCO's "
            f"{row.get('alert_month')} alert, after testing by {row.get('tested_by')}. In plain words: {meaning}.")


def explain_alert(row: dict) -> dict:
    """Plain-language explanation grounded ONLY in the cited alert row."""
    if mode() == "gemini":
        prompt = f"""Explain this official drug-quality alert to a patient in 2-3 short, calm sentences.
Use ONLY the facts below. Do not add facts, do not give medical advice, do not say whether to stop or
continue the medicine, do not mention dose. Say what failed and what that means in everyday words.

Product: {row.get('product')}
Batch: {row.get('batch')}
Alert month: {row.get('alert_month')} ({row.get('list_type')} list)
Tested by: {row.get('tested_by')}
Reason recorded by the lab: {row.get('failure_reason')}
Remarks: {row.get('remarks') or '-'}"""
        try:
            text = _gemini_text(prompt)
            if text and not _BANNED.search(text):
                return {"text": text, "advice": ADVICE, "source": f"gemini ({MODEL})"}
        except Exception:
            pass
    return {"text": _rule_explain(row), "advice": ADVICE, "source": "rule-based (offline)"}


# ---------------------------------------------------------------- drafts
def draft_supplier_return(org: str, supplier: str, items: list) -> dict:
    lines = "\n".join(f"- {i['product']}, batch {i['batch']}, qty {i['qty']} "
                      f"(CDSCO alert: {i['citation']}; reason: {(i.get('failure_reason') or '').strip()[:120]})"
                      for i in items)
    subject = f"Return request: {len(items)} batch(es) listed in CDSCO quality alerts"
    template = (f"Dear {supplier} team,\n\nDuring our routine check against CDSCO's published drug alerts, "
                f"the following batches supplied to {org} appear in the Not of Standard Quality / spurious lists:\n\n"
                f"{lines}\n\nWe have moved these batches to quarantine and request a return and credit note. "
                f"Please confirm collection and share your investigation reference.\n\nRegards,\n{org}")
    if mode() == "gemini":
        try:
            text = _gemini_text(f"""Rewrite this pharmacy-to-supplier return request as a clear, polite,
professional email body. Keep every batch line and reference exactly as given. No new facts. Plain text only.

{template}""")
            if text and all(i["batch"] in text for i in items):
                return {"subject": subject, "body": text, "source": f"gemini ({MODEL})"}
        except Exception:
            pass
    return {"subject": subject, "body": template, "source": "template (offline)"}


def draft_controller_report(reporter: str, item: dict, row: dict) -> dict:
    subject = f"Report: medicine from a CDSCO-listed batch found in the market ({row.get('batch')})"
    body = (f"To the State Drug Controller,\n\nI found the following medicine with a batch number that appears "
            f"in a published CDSCO alert:\n\n- Product on pack: {item.get('product')}\n"
            f"- Batch on pack: {item.get('batch')}\n- Manufacturer on pack: {item.get('manufacturer')}\n"
            f"- Expiry on pack: {item.get('expiry')}\n- Matching alert: {row.get('citation')} "
            f"({row.get('alert_month')}, {row.get('list_type')} list; reason: {row.get('failure_reason')})\n\n"
            f"Please advise whether this stock should be withdrawn locally.\n\nSubmitted via BatchWatch on behalf "
            f"of a member of the public (contact details withheld until they choose to share them).")
    return {"subject": subject, "body": body, "source": "template"}

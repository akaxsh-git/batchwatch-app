"""Deterministic verdict engine. The LLM never makes this decision.

FLAGGED  batch matches exactly AND product or manufacturer agrees
POSSIBLE batch differs only by a likely OCR misread (0/O, 1/I...), is >=90% similar,
         or matches but the product/manufacturer disagrees -> ask a human to confirm
CLEAR    not found in any *live* (admin-approved) alert. Never means "safe".
"""
import re

from rapidfuzz import fuzz

from .db import session
from .parser import norm_batch

CONFUSABLE = str.maketrans({"O": "0", "Q": "0", "D": "0", "I": "1", "L": "1",
                            "S": "5", "B": "8", "Z": "2", "G": "6"})
NAME_AGREEMENT_MIN = 60
# some alert rows have no real batch ("Not mentioned", "NA"); never match on those
PLACEHOLDER_BATCHES = {"NOTMENTIONED", "NA", "NIL", "NOTAVAILABLE", "UNKNOWN", "NONE", "NOTKNOWN"}
NEAR_MIN = 90

_cache = {"key": None, "rows": [], "by_batch": {}, "by_ocr": {}}


def _live_key():
    with session() as con:
        return con.execute("SELECT COUNT(*), COALESCE(MAX(reviewed_at),'') FROM ingests WHERE status='live'").fetchone()[:]


def _load():
    key = tuple(_live_key())
    if _cache["key"] == key:
        return _cache
    with session() as con:
        rows = [dict(r) for r in con.execute(
            """SELECT a.* FROM alerts a JOIN ingests i ON i.id=a.ingest_id
               WHERE i.status='live'""")]
    by_batch, by_ocr = {}, {}
    rows = [r for r in rows if r["batch_norm"] not in PLACEHOLDER_BATCHES and len(r["batch_norm"]) >= 3]
    for r in rows:
        by_batch.setdefault(r["batch_norm"], []).append(r)
        by_ocr.setdefault(ocr_key(r["batch_norm"]), []).append(r)
    _cache.update(key=key, rows=rows, by_batch=by_batch, by_ocr=by_ocr)
    return _cache


def invalidate():
    _cache["key"] = None


def ocr_key(s: str) -> str:
    return norm_batch(s).translate(CONFUSABLE)


def citation(r: dict) -> str:
    return f"{r['source_file']} · S.No {r['sno']} · page {r['page']}"


# words that appear on almost every label and say nothing about *which* drug or company
_PRODUCT_STOP = {"tablet", "tablets", "tab", "tabs", "capsule", "capsules", "cap", "caps", "syrup",
                 "suspension", "oral", "injection", "inj", "ip", "bp", "usp", "and", "with", "gastro",
                 "resistant", "dispersible", "film", "coated", "sustained", "release", "chewable", "drops",
                 "solution", "cream", "gel", "ointment", "powder", "sodium", "hydrochloride", "the", "for",
                 "paediatric", "pediatric", "mg", "ml", "gm", "mcg", "vitamin", "vitamins",
                 "multivitamin", "acid", "tab", "tablet", "softgel", "soft", "gelatin"}
_MAKER_STOP = {"pvt", "ltd", "limited", "private", "pharma", "pharmaceutical", "pharmaceuticals",
               "laboratories", "laboratory", "labs", "lab", "healthcare", "health", "lifesciences",
               "life", "sciences", "science", "remedies", "biotech", "formulations", "industries",
               "india", "unit", "plot", "the", "and", "llp", "inc", "company", "drugs", "medicare"}


def _tokens(s, stop):
    words = re.findall(r"[a-z0-9]+", (s or "").lower())
    # keep real words (3+ letters) and short strength codes like d3 / b12, drop pure numbers
    return [w for w in words if w not in stop and re.search(r"[a-z]", w)
            and (len(w) >= 3 or re.search(r"\d", w))]


def _overlap(label_tokens, alert_tokens):
    """Share of the label's meaningful words that appear (fuzzily) in the alert row."""
    if not label_tokens or not alert_tokens:
        return None
    hit = sum(1 for t in label_tokens if max(fuzz.ratio(t, a) for a in alert_tokens) >= 85)
    return round(100 * hit / len(label_tokens))


def _name_score(product, maker, r):
    """0-100 agreement between the label and the alert row, or None if nothing to compare.
    Uses only distinctive words (drug names, company names), not 'tablets', 'IP', 'Pvt Ltd'."""
    scores = []
    if product:
        s = _overlap(_tokens(product, _PRODUCT_STOP), _tokens(r["product"], _PRODUCT_STOP))
        if s is not None:
            scores.append(s)
    if maker:
        # only the first ~6 words of the alert's manufacturer field (the rest is the address)
        alert_maker = " ".join((r["manufacturer"] or "").split()[:6])
        s = _overlap(_tokens(maker, _MAKER_STOP), _tokens(alert_maker, _MAKER_STOP))
        if s is not None:
            scores.append(s)
    return max(scores) if scores else None


def match(batch: str, product: str = None, manufacturer: str = None) -> dict:
    data = _load()
    b = norm_batch(batch)
    if len(b) < 3:
        return {"verdict": "RETAKE", "reason": "Batch number too short to check reliably.",
                "matches": [], "citation": None}
    exact = data["by_batch"].get(b, [])
    ocr = [r for r in data["by_ocr"].get(ocr_key(b), []) if r["batch_norm"] != b]
    seen = {id(r) for r in exact + ocr}
    near = []
    if len(b) >= 4:
        for r in data["rows"]:
            if id(r) in seen or len(r["batch_norm"]) < 4 or abs(len(r["batch_norm"]) - len(b)) > 1:
                continue
            if fuzz.ratio(r["batch_norm"], b) >= NEAR_MIN:
                near.append(r)
    results = []
    for kind, group in (("exact", exact), ("ocr_lookalike", ocr), ("near", near)):
        for r in group:
            ns = _name_score(product, manufacturer, r)
            # FLAGGED needs an exact batch AND agreement on the name. If the label gave a name but
            # nothing distinctive could be compared, a human must confirm (POSSIBLE).
            agrees = (ns >= NAME_AGREEMENT_MIN) if ns is not None else not (product or manufacturer)
            level = "FLAGGED" if kind == "exact" and agrees else "POSSIBLE"
            results.append({
                "level": level, "batch_match": kind, "name_agreement": ns, "alert_id": r["id"],
                "alert_month": r["alert_month"], "list_type": r["list_type"], "citation": citation(r),
                "product": r["product"], "batch": r["batch"], "manufacturer": r["manufacturer"],
                "mfg_date": r["mfg_date"], "exp_date": r["exp_date"], "failure_reason": r["nsq_result"],
                "tested_by": r["reporting_lab_state"], "remarks": r["remarks"],
            })
    order = {"FLAGGED": 0, "POSSIBLE": 1}
    results.sort(key=lambda x: (order[x["level"]], -(x["name_agreement"] or 0), x["alert_month"]))
    if any(r["level"] == "FLAGGED" for r in results):
        verdict = "FLAGGED"
    elif results:
        verdict = "POSSIBLE"
    else:
        verdict = "CLEAR"
    top = results[0] if results else None
    times_flagged = len({(r["alert_month"], r["list_type"]) for r in results if r["level"] == "FLAGGED"})
    return {"verdict": verdict, "query": {"batch": batch, "product": product, "manufacturer": manufacturer},
            "citation": top["citation"] if top else None, "alert_id": top["alert_id"] if top else None,
            "times_flagged": times_flagged, "matches": results[:5]}


VERDICT_TEXT = {
    "FLAGGED": "Found in a published CDSCO alert",
    "POSSIBLE": "Possible match: please check the batch number on the pack",
    "CLEAR": "Not found in published alerts",
    "RETAKE": "Batch number unreadable",
}

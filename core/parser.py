"""Alert PDF parser (config-driven).

How it works:
1. Every table cell in these PDFs is drawn as a shaded rectangle.
2. Rectangles sharing the same top and bottom edge form one table row
   (only full-width rows are kept; thin borders and nested stripes are dropped).
3. Each word is placed in the rectangle that contains its centre point.
4. The header row (a cell reading exactly "Batch No") tells us which column
   is which, using the keywords in sources/<source>.yaml.
5. A row with an empty serial number is a spill-over (usually across a page
   break) and is appended to the previous record.
6. Batch numbers are normalised to A-Z0-9 so formatting differences don't matter.
"""
import collections
import re
from pathlib import Path

import pdfplumber
import yaml

from .paths import SOURCES_DIR

FIELDS = ["sno", "product", "batch", "mfg_date", "exp_date", "manufacturer",
          "nsq_result", "reporting_source", "reporting_lab_state",
          "reporting_month", "remarks"]

_KEEP_SHORT = {"of", "to", "in", "on", "at", "by", "as", "is", "an", "or", "be",
               "no", "mg", "ml", "gm", "g", "i", "a", "it", "if", "we", "up", "do"}


def load_source(name: str = "cdsco") -> dict:
    with open(Path(SOURCES_DIR) / f"{name}.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def norm_batch(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def _letters(s: str) -> str:
    return re.sub(r"[^a-z]", "", (s or "").lower())


def _is_black(r) -> bool:
    c = r.get("non_stroking_color")
    if isinstance(c, (list, tuple)):
        return len(c) > 0 and all(v == 0 for v in c)
    return c == 0


def _row_bands(page):
    rects = [r for r in page.rects if r["width"] > 12 and r["height"] > 10 and not _is_black(r)]
    groups = collections.defaultdict(list)
    for r in rects:
        groups[(round(r["top"]), round(r["bottom"]))].append(r)
    if not groups:
        return []
    ncols = max(len(v) for v in groups.values())
    full = [(t, b, sorted(c, key=lambda r: r["x0"])) for (t, b), c in groups.items() if len(c) == ncols]
    keep = [(t, b, c) for t, b, c in full
            if not any(t2 <= t and b <= b2 and (t2, b2) != (t, b) for t2, b2, _ in full)]
    return sorted(keep, key=lambda x: x[0])


def _cell_text(words, cell) -> str:
    inside = [w for w in words
              if cell["x0"] - 1 <= (w["x0"] + w["x1"]) / 2 <= cell["x1"] + 1
              and cell["top"] - 1 <= (w["top"] + w["bottom"]) / 2 <= cell["bottom"] + 1]
    inside.sort(key=lambda w: (round(w["top"]), w["x0"]))
    return " ".join(w["text"] for w in inside).strip()


def _header_field(text: str, cfg: dict):
    k = _letters(text)
    if not k:
        return None
    for field, keywords in cfg["header_keywords"]:
        if field == "sno":
            if k.startswith("sn") or k == "sno":
                return "sno"
            continue
        if any(kw in k for kw in keywords):
            return field
    return None


def _is_header(texts, cfg) -> bool:
    cells = [_letters(t) for t in texts]
    return any(c in cfg["header_marker_cells"] for c in cells) and not re.fullmatch(r"\d+", texts[0] or "")


def _fix_split_words(s: str) -> str:
    def repl(m):
        return m.group(0) if m.group(2) in _KEEP_SHORT else m.group(1) + m.group(2)
    return re.sub(r"([A-Za-z]{4,}) ([a-z]{1,2})\b", repl, s or "").strip()


def _join_broken(s: str) -> str:
    return re.sub(r"-\s+", "-", s or "").strip()


def parse_pdf(path, source: str = "cdsco") -> list:
    """Return a list of alert records (dicts) from one alert PDF."""
    cfg = load_source(source)
    records, mapping = [], None
    with pdfplumber.open(str(path)) as pdf:
        for pno, page in enumerate(pdf.pages, start=1):
            words = page.extract_words()
            for _, _, cells in _row_bands(page):
                texts = [_cell_text(words, c) for c in cells]
                if _is_header(texts, cfg):
                    mapping = [_header_field(t, cfg) for t in texts]
                    continue
                if mapping is None or len(mapping) != len(texts):
                    continue
                row = {f: "" for f in FIELDS}
                for field, txt in zip(mapping, texts):
                    if field:
                        row[field] = (row[field] + " " + txt).strip()
                if not any(row.values()):
                    continue
                if re.fullmatch(r"\d+", row["sno"] or ""):
                    row["page"] = pno
                    records.append(row)
                elif records:
                    prev = records[-1]
                    for f in FIELDS:
                        if f != "sno" and row[f]:
                            prev[f] = (prev[f] + " " + row[f]).strip()
    for r in records:
        for f in ("product", "nsq_result", "manufacturer", "remarks"):
            r[f] = _fix_split_words(r[f])
        r["reporting_month"] = _join_broken(r["reporting_month"]).replace(" ", "")
        m = re.search(r"Manufacturing\s*Date\s*:?\s*([A-Za-z]{3}-?\s*\d{4})", r["mfg_date"])
        e = re.search(r"Expiry\s*Date\s*:?\s*([A-Za-z]{3}-?\s*\d{4})", r["mfg_date"])
        if m:
            r["mfg_date"] = m.group(1)
        if e and not r["exp_date"]:
            r["exp_date"] = e.group(1)
        r["batch"] = _join_broken(r["batch"])
        r["exp_date"] = _join_broken(r["exp_date"]).replace(" ", "")
        r["mfg_date"] = _join_broken(r["mfg_date"]).replace(" ", "")
        r["batch_norm"] = norm_batch(r["batch"])
        r["sno"] = int(r["sno"])
    return records


def validate(records: list) -> dict:
    """Completeness check: serial numbers must run 1..N with no gaps or repeats."""
    snos = [r["sno"] for r in records]
    mx = max(snos) if snos else 0
    missing = sorted(set(range(1, mx + 1)) - set(snos))
    dupes = sorted({s for s in snos if snos.count(s) > 1})
    empty_batch = sum(1 for r in records if not r["batch_norm"])
    ok = bool(records) and not missing and not dupes and empty_batch == 0
    return {"rows": len(records), "max_sno": mx, "missing": missing, "duplicates": dupes,
            "empty_batch": empty_batch, "passed": ok}

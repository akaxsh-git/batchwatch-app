"""Alert ingestion with a human approval gate.

ingest_file  -> parses and validates a PDF; stores rows as *pending*.
approve      -> admin approves; data goes *live* and every saved inventory and
               cabinet is re-checked automatically.
Pending or rejected data is never used for matching.
"""
import hashlib
import json
import re
from pathlib import Path

from . import auth
from .audit import audited, log, now
from .db import session
from .parser import load_source, parse_pdf, validate
from .paths import INBOX_DIR, ALERTS_DIR


def _sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def known_files() -> set:
    with session() as con:
        return {r[0] for r in con.execute("SELECT source_file FROM ingests")}


def scan_inbox(source="cdsco") -> list:
    """New alert PDFs in data/inbox that haven't been ingested yet."""
    cfg = load_source(source)
    seen = known_files()
    return sorted(p for p in Path(INBOX_DIR).glob("*.pdf")
                  if re.match(cfg["file_pattern"], p.name) and p.name not in seen)


@audited("ingest_alert_file", summarize_input=lambda path, **k: {"file": Path(path).name},
         summarize_output=lambda r: {k: r[k] for k in ("ingest_id", "rows", "validation", "status")})
def ingest_file(actor, path, source="cdsco") -> dict:
    auth.require(actor, "ingest_alerts")
    cfg = load_source(source)
    path = Path(path)
    m = re.match(cfg["file_pattern"], path.name)
    if not m:
        raise ValueError(f"{path.name} does not match the expected file pattern")
    if path.name in known_files():
        raise ValueError(f"{path.name} was already ingested")
    records = parse_pdf(path, source)
    v = validate(records)
    with session() as con:
        cur = con.execute(
            """INSERT INTO ingests(source, source_file, alert_month, list_type, sha256, rows,
               max_sno, missing, validation, status, ingested_by, ingested_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (source, path.name, m["month"], m["list_type"], _sha256(path), v["rows"], v["max_sno"],
             json.dumps(v["missing"]), "passed" if v["passed"] else "failed", "pending",
             actor["name"], now()))
        ingest_id = cur.lastrowid
        con.executemany(
            """INSERT INTO alerts(ingest_id, alert_month, list_type, source_file, page, sno, product,
               batch, batch_norm, mfg_date, exp_date, manufacturer, nsq_result, reporting_source,
               reporting_lab_state, reporting_month, remarks)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [(ingest_id, m["month"], m["list_type"], path.name, r["page"], r["sno"], r["product"],
              r["batch"], r["batch_norm"], r["mfg_date"], r["exp_date"], r["manufacturer"],
              r["nsq_result"], r["reporting_source"], r["reporting_lab_state"],
              r["reporting_month"], r["remarks"]) for r in records])
    return {"ingest_id": ingest_id, "file": path.name, "month": m["month"], "list_type": m["list_type"],
            "status": "pending", "validation": "passed" if v["passed"] else "failed", **v}


def list_ingests(status=None) -> list:
    q, p = "SELECT * FROM ingests", []
    if status:
        q += " WHERE status=?"; p.append(status)
    q += " ORDER BY alert_month DESC, list_type"
    with session() as con:
        return [dict(r) for r in con.execute(q, p)]


@audited("approve_alert_data", summarize_input=lambda ingest_id, **k: {"ingest_id": ingest_id})
def approve(actor, ingest_id: int, run_recheck=True) -> dict:
    """Human gate: an admin must approve new alert data before it is used."""
    auth.require(actor, "approve_ingest")
    with session() as con:
        ing = con.execute("SELECT * FROM ingests WHERE id=?", (ingest_id,)).fetchone()
        if not ing:
            raise ValueError("No such ingest")
        if ing["validation"] != "passed":
            raise ValueError("Validation failed (missing or duplicate serial numbers); cannot go live")
        if ing["status"] == "live":
            return {"ingest_id": ingest_id, "status": "live", "recheck": None}
        con.execute("UPDATE ingests SET status='live', reviewed_by=?, reviewed_at=? WHERE id=?",
                    (actor["name"], now(), ingest_id))
    # file moves from inbox to the reviewed folder
    src = Path(INBOX_DIR) / ing["source_file"]
    if src.exists():
        Path(ALERTS_DIR).mkdir(parents=True, exist_ok=True)
        src.rename(Path(ALERTS_DIR) / ing["source_file"])
    summary = None
    if run_recheck:
        from .recheck import recheck_all
        summary = recheck_all(reason=f"new alert data approved: {ing['source_file']}")
    return {"ingest_id": ingest_id, "status": "live", "recheck": summary}


@audited("reject_alert_data", summarize_input=lambda ingest_id, reason="", **k: {"ingest_id": ingest_id, "reason": reason})
def reject(actor, ingest_id: int, reason: str = "") -> dict:
    auth.require(actor, "approve_ingest")
    with session() as con:
        con.execute("UPDATE ingests SET status='rejected', reviewed_by=?, reviewed_at=? WHERE id=?",
                    (actor["name"], now(), ingest_id))
        con.execute("DELETE FROM alerts WHERE ingest_id=?", (ingest_id,))
    return {"ingest_id": ingest_id, "status": "rejected"}


def stats() -> dict:
    with session() as con:
        live = con.execute("""SELECT COUNT(*) n, COUNT(DISTINCT a.alert_month) months,
               MIN(a.alert_month) first, MAX(a.alert_month) last FROM alerts a
               JOIN ingests i ON i.id=a.ingest_id WHERE i.status='live'""").fetchone()
        by_type = con.execute("""SELECT a.list_type, COUNT(*) FROM alerts a JOIN ingests i
               ON i.id=a.ingest_id WHERE i.status='live' GROUP BY 1""").fetchall()
        pending = con.execute("SELECT COUNT(*) FROM ingests WHERE status='pending'").fetchone()[0]
    return {"live_rows": live["n"], "months": live["months"], "first": live["first"],
            "last": live["last"], "by_type": {k: v for k, v in by_type}, "pending_files": pending}

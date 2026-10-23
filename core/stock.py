"""Stock mode (B2B): check an organisation's inventory against live alerts."""
import time

import pandas as pd

from . import auth
from .audit import audited, log, now
from .db import session
from .matcher import match

COLUMN_ALIASES = {
    "sku": ["sku", "item code", "item_code", "code"],
    "product": ["product", "product name", "item", "medicine", "drug", "name"],
    "batch": ["batch", "batch no", "batch_no", "batch number", "lot", "lot no"],
    "manufacturer": ["manufacturer", "mfr", "maker", "company", "manufactured by"],
    "qty": ["qty", "quantity", "stock", "units"],
    "supplier": ["supplier", "distributor", "vendor"],
    "supplier_email": ["supplier_email", "supplier email", "email"],
}


def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    lower = {c.lower().strip(): c for c in df.columns}
    out = pd.DataFrame()
    for field, aliases in COLUMN_ALIASES.items():
        src = next((lower[a] for a in aliases if a in lower), None)
        out[field] = df[src] if src is not None else None
    if out["batch"].isna().all():
        raise ValueError("The file needs a batch number column (e.g. 'batch' or 'batch no').")
    out["qty"] = pd.to_numeric(out["qty"], errors="coerce").fillna(0).astype(int)
    return out.fillna("")


@audited("tool:check_inventory",
         summarize_input=lambda df, **k: {"lines": len(df)},
         summarize_output=lambda r: {k: r[k] for k in ("org", "lines", "counts", "seconds")})
def check_inventory(actor, df: pd.DataFrame) -> dict:
    """Replace the org's inventory with this upload and check every line."""
    auth.require(actor, "check_stock")
    org = actor["org"]
    t0 = time.perf_counter()
    inv = normalise_columns(df)
    rows, counts = [], {"FLAGGED": 0, "POSSIBLE": 0, "CLEAR": 0, "RETAKE": 0}
    for rec in inv.to_dict("records"):
        res = match(str(rec["batch"]), str(rec["product"]) or None, str(rec["manufacturer"]) or None)
        counts[res["verdict"]] += 1
        rows.append((org, str(rec["sku"]), str(rec["product"]), str(rec["batch"]), str(rec["manufacturer"]),
                     int(rec["qty"]), str(rec["supplier"]), str(rec["supplier_email"]),
                     res["verdict"], res["citation"], res["alert_id"], now()))
    with session() as con:
        con.execute("DELETE FROM inventory WHERE org=?", (org,))
        con.executemany("""INSERT INTO inventory(org, sku, product, batch, manufacturer, qty, supplier,
                           supplier_email, verdict, citation, alert_id, checked_at)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", rows)
    secs = round(time.perf_counter() - t0, 2)
    return {"org": org, "lines": len(rows), "counts": counts, "seconds": secs}


def get_inventory(actor) -> pd.DataFrame:
    auth.require(actor, "check_stock")
    with session() as con:
        df = pd.read_sql_query(
            """SELECT i.id, i.sku, i.product, i.batch, i.manufacturer, i.qty, i.supplier, i.verdict,
                      i.status, i.citation, a.nsq_result AS failure_reason, a.alert_month,
                      a.reporting_lab_state AS tested_by, i.supplier_email, i.alert_id
               FROM inventory i LEFT JOIN alerts a ON a.id=i.alert_id
               WHERE i.org=? ORDER BY CASE i.verdict WHEN 'FLAGGED' THEN 0 WHEN 'POSSIBLE' THEN 1 ELSE 2 END, i.id""",
            con, params=(actor["org"],))
    return df


@audited("human:quarantine_stock", summarize_input=lambda ids, **k: {"inventory_ids": ids})
def quarantine(actor, ids: list) -> dict:
    """Pharmacist decision: move flagged lines to quarantine (off sale)."""
    auth.require(actor, "quarantine")
    with session() as con:
        n = 0
        for i in ids:
            n += con.execute("UPDATE inventory SET status='quarantined' WHERE id=? AND org=?",
                             (int(i), actor["org"])).rowcount
    return {"quarantined": n}

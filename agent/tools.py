"""The agent's tools. Every call is permission-checked and written to the audit log."""
from collections import defaultdict

from core import actions, auth, matcher, stock
from core.audit import audited
from . import llm


@audited("tool:read_label",
         summarize_input=lambda image_bytes, filename="", **k: {"file": filename, "bytes": len(image_bytes)},
         summarize_output=lambda r: {"batch": r["fields"].get("batch_number"),
                                     "batch_conf": r["confidence"].get("batch_number"), "source": r["source"],
                                     "note": r.get("note")})
def read_label(actor, image_bytes: bytes, filename: str = "") -> dict:
    auth.require(actor, "scan_label")
    return llm.read_label(image_bytes, filename)


@audited("tool:match_batch", summarize_output=lambda r: {"verdict": r["verdict"], "citation": r["citation"],
                                                          "candidates": len(r["matches"])})
def match_batch(actor, batch: str, product: str = None, manufacturer: str = None) -> dict:
    return matcher.match(batch, product, manufacturer)


@audited("tool:explain_alert", summarize_input=lambda row, **k: {"citation": row.get("citation")},
         summarize_output=lambda r: {"source": r["source"], "chars": len(r["text"])})
def explain_alert(actor, row: dict) -> dict:
    return llm.explain_alert(row)


def draft_controller_report(actor, item: dict, row: dict) -> dict:
    d = llm.draft_controller_report(actor["name"], item, row)
    created = actions.create_draft(actor, "controller_report", "State Drug Controller", d["subject"], d["body"],
                                   [{**item, "citation": row.get("citation")}])
    return {**d, **created}


def draft_supplier_returns(actor) -> list:
    """Group the org's flagged, in-stock lines by supplier and draft one return request each."""
    auth.require(actor, "draft_supplier_return")
    inv = stock.get_inventory(actor)
    flagged = inv[(inv.verdict == "FLAGGED")]
    by_supplier = defaultdict(list)
    for r in flagged.to_dict("records"):
        by_supplier[(r["supplier"] or "Unknown supplier", r["supplier_email"] or "")].append(r)
    out = []
    for (supplier, email), items in by_supplier.items():
        d = llm.draft_supplier_return(actor["org"], supplier, items)
        created = actions.create_draft(actor, "supplier_return", f"{supplier} <{email}>", d["subject"], d["body"],
                                       [{"inventory_id": i["id"], "product": i["product"], "batch": i["batch"],
                                         "qty": i["qty"], "citation": i["citation"]} for i in items])
        out.append({**d, **created, "supplier": supplier, "items": items})
    return out

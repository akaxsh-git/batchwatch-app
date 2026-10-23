"""Monthly compliance report (outcome reporting)."""
import json

from . import auth
from .audit import audited, now
from .db import session


@audited("compliance_report", summarize_output=lambda r: {"org": r["org"], "flagged": r["counts"].get("FLAGGED", 0)})
def compliance_report(actor, org: str = None) -> dict:
    if actor["role"] == "pharmacist":
        auth.require(actor, "compliance_report_org")
        org = actor["org"]
    else:
        auth.require(actor, "compliance_report_any")
        if not org:
            raise ValueError("Choose an organisation")
    with session() as con:
        inv = [dict(r) for r in con.execute(
            """SELECT i.*, a.nsq_result, a.alert_month FROM inventory i LEFT JOIN alerts a ON a.id=i.alert_id
               WHERE org=? ORDER BY i.verdict, i.product""", (org,))]
        actions = [dict(r) for r in con.execute("SELECT * FROM actions WHERE org=? ORDER BY id", (org,))]
        sources = [dict(r) for r in con.execute(
            "SELECT source_file, rows, reviewed_by, reviewed_at FROM ingests WHERE status='live' ORDER BY source_file")]
        audit_n = con.execute("SELECT COUNT(*) FROM audit_log WHERE org=?", (org,)).fetchone()[0]
    counts = {}
    for r in inv:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    flagged = [r for r in inv if r["verdict"] in ("FLAGGED", "POSSIBLE")]
    q = sum(1 for r in flagged if r["status"] == "quarantined")

    lines = [f"# BatchWatch compliance report: {org}", "",
             f"Generated {now()} by {actor['name']} ({actor['role']}).", "",
             "## Summary", "",
             f"- Inventory lines checked: **{len(inv)}**",
             f"- FLAGGED: **{counts.get('FLAGGED', 0)}** · POSSIBLE: **{counts.get('POSSIBLE', 0)}** · "
             f"CLEAR (not in published alerts): **{counts.get('CLEAR', 0)}**",
             f"- Flagged/possible lines quarantined: **{q} of {len(flagged)}**",
             f"- Supplier return drafts: {sum(1 for a in actions if a['kind']=='supplier_return')} "
             f"(approved {sum(1 for a in actions if a['status']=='approved')}, "
             f"rejected {sum(1 for a in actions if a['status']=='rejected')})",
             f"- Audit log entries for this organisation: {audit_n}", "",
             "## Flagged and possible lines", "",
             "| Product | Batch | Verdict | Status | Failure reason | Source |",
             "|---|---|---|---|---|---|"]
    for r in flagged:
        reason = (r["nsq_result"] or "").replace("|", "/")[:90]
        lines.append(f"| {r['product']} | {r['batch']} | {r['verdict']} | {r['status']} | {reason} | {r['citation'] or ''} |")
    lines += ["", "## Actions", ""]
    for a in actions:
        lines.append(f"- #{a['id']} {a['kind']} to {a['recipient']}: **{a['status']}**"
                     + (f" by {a['decided_by']} at {a['decided_at']}" if a["decided_by"] else ""))
    if not actions:
        lines.append("- None")
    lines += ["", "## Alert data used (admin-approved)", ""]
    for s in sources:
        lines.append(f"- {s['source_file']}: {s['rows']} rows, approved by {s['reviewed_by']} at {s['reviewed_at']}")
    lines += ["", "_CLEAR means not found in published CDSCO alerts; it is not a certification of quality._"]
    return {"org": org, "counts": counts, "markdown": "\n".join(lines), "flagged": flagged}

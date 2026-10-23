"""Drafts prepared by the agent (supplier returns, reports to the drug
controller). Nothing is sent until the responsible person approves."""
import json

from . import auth
from .audit import audited, now
from .db import session
from .notify import send_email


@audited("create_draft", summarize_input=lambda kind, recipient, subject, body, items, **k:
         {"kind": kind, "recipient": recipient, "subject": subject, "items": len(items or [])})
def create_draft(actor, kind, recipient, subject, body, items) -> dict:
    auth.require(actor, "draft_supplier_return" if kind == "supplier_return" else "draft_controller_report")
    with session() as con:
        cur = con.execute("""INSERT INTO actions(kind, owner, org, recipient, subject, body, items, status,
                             created_at) VALUES (?,?,?,?,?,?,?, 'draft', ?)""",
                          (kind, actor["name"], actor.get("org"), recipient, subject, body,
                           json.dumps(items, default=str), now()))
    return {"action_id": cur.lastrowid, "status": "draft"}


def list_actions(actor, status=None) -> list:
    q, p = "SELECT * FROM actions WHERE ", []
    if actor["role"] == "pharmacist":
        q += "org=?"; p.append(actor["org"])
    elif actor["role"] == "household":
        q += "owner=?"; p.append(actor["name"])
    else:
        q += "1=1"
    if status:
        q += " AND status=?"; p.append(status)
    with session() as con:
        return [dict(r) for r in con.execute(q + " ORDER BY id DESC", p)]


@audited("decide_draft", summarize_input=lambda action_id, approve, body=None, **k:
         {"action_id": action_id, "approve": approve, "edited": body is not None})
def decide(actor, action_id: int, approve: bool, body: str = None) -> dict:
    """Human gate: approve (send) or reject a draft. Only its owner/org may decide."""
    auth.require(actor, "decide_own_actions")
    with session() as con:
        a = con.execute("SELECT * FROM actions WHERE id=?", (action_id,)).fetchone()
        if not a:
            raise ValueError("No such draft")
        mine = (a["org"] == actor.get("org")) if actor["role"] == "pharmacist" else (a["owner"] == actor["name"])
        if not mine:
            raise PermissionError("You can only decide your own drafts")
        if a["status"] != "draft":
            return {"action_id": action_id, "status": a["status"]}
        status = "approved" if approve else "rejected"
        con.execute("UPDATE actions SET status=?, body=COALESCE(?, body), decided_by=?, decided_at=? WHERE id=?",
                    (status, body, actor["name"], now(), action_id))
    emailed = send_email(a["subject"], body or a["body"]) if approve else False
    return {"action_id": action_id, "status": status, "emailed": emailed}

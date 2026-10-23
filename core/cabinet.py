"""Household mode: a family's saved medicines."""
from . import auth
from .audit import audited, now
from .db import session


@audited("save_to_cabinet")
def add(actor, product, batch, manufacturer, expiry, verdict, citation, alert_id) -> dict:
    auth.require(actor, "manage_cabinet")
    with session() as con:
        cur = con.execute("""INSERT INTO cabinet(owner, product, batch, manufacturer, expiry, verdict,
                             citation, alert_id, added_at, checked_at) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                          (actor["name"], product, batch, manufacturer, expiry, verdict, citation,
                           alert_id, now(), now()))
    return {"cabinet_id": cur.lastrowid, "verdict": verdict, "citation": citation}


def list_items(actor) -> list:
    auth.require(actor, "manage_cabinet")
    with session() as con:
        return [dict(r) for r in con.execute(
            """SELECT c.*, a.nsq_result AS failure_reason, a.alert_month FROM cabinet c
               LEFT JOIN alerts a ON a.id=c.alert_id WHERE owner=? ORDER BY c.id DESC""",
            (actor["name"],))]


@audited("remove_from_cabinet")
def remove(actor, cabinet_id: int) -> dict:
    auth.require(actor, "manage_cabinet")
    with session() as con:
        n = con.execute("DELETE FROM cabinet WHERE id=? AND owner=?", (cabinet_id, actor["name"])).rowcount
    return {"removed": n}

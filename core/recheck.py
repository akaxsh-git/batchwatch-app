"""Monthly re-check: when new alert data goes live, re-match every saved
inventory line and cabinet item. Notify only when a verdict changes."""
from .audit import log, now
from .db import SYSTEM, session
from .matcher import invalidate, match
from .notify import notify

RANK = {"CLEAR": 0, "RETAKE": 0, "POSSIBLE": 1, "FLAGGED": 2}


def recheck_all(reason: str = "scheduled") -> dict:
    invalidate()
    changes = {"inventory": 0, "cabinet": 0, "newly_flagged": 0, "checked": 0}
    with session() as con:
        inv = [dict(r) for r in con.execute("SELECT * FROM inventory")]
        cab = [dict(r) for r in con.execute("SELECT * FROM cabinet")]
    for item in inv:
        res = match(item["batch"], item["product"], item["manufacturer"])
        changes["checked"] += 1
        if res["verdict"] != item["verdict"]:
            changes["inventory"] += 1
            with session() as con:
                con.execute("UPDATE inventory SET verdict=?, citation=?, alert_id=?, checked_at=? WHERE id=?",
                            (res["verdict"], res["citation"], res["alert_id"], now(), item["id"]))
            if RANK[res["verdict"]] > RANK.get(item["verdict"], 0):
                if res["verdict"] == "FLAGGED":
                    changes["newly_flagged"] += 1
                notify(recipient=None, org=item["org"], verdict=res["verdict"], ref=f"inventory:{item['id']}",
                       message=f"{item['product']} batch {item['batch']} is now {res['verdict']} "
                               f"({res['citation']}). Review and quarantine if confirmed.")
            log({**SYSTEM, "org": item["org"]}, "tool:recheck_inventory_item",
                {"item": item["id"], "batch": item["batch"], "before": item["verdict"]},
                {"after": res["verdict"]}, verdict=res["verdict"], citation=res["citation"])
    for item in cab:
        res = match(item["batch"], item["product"], item["manufacturer"])
        changes["checked"] += 1
        if res["verdict"] != item["verdict"]:
            changes["cabinet"] += 1
            with session() as con:
                con.execute("UPDATE cabinet SET verdict=?, citation=?, alert_id=?, checked_at=? WHERE id=?",
                            (res["verdict"], res["citation"], res["alert_id"], now(), item["id"]))
            if RANK[res["verdict"]] > RANK.get(item["verdict"], 0):
                if res["verdict"] == "FLAGGED":
                    changes["newly_flagged"] += 1
                notify(recipient=item["owner"], org=None, verdict=res["verdict"], ref=f"cabinet:{item['id']}",
                       message=f"A medicine in your cabinet ({item['product']}, batch {item['batch']}) now "
                               f"appears in a CDSCO alert. Please speak to your pharmacist or doctor "
                               f"before taking more.")
            log({**SYSTEM, "name": SYSTEM["name"]}, "tool:recheck_cabinet_item",
                {"owner": item["owner"], "batch": item["batch"], "before": item["verdict"]},
                {"after": res["verdict"]}, verdict=res["verdict"], citation=res["citation"])
    log(SYSTEM, "tool:monthly_recheck", {"reason": reason}, changes)
    return changes

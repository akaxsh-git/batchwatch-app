"""Agent workflows end to end in offline mode (no API key needed)."""
import uuid

import pandas as pd

from agent.graphs import Agent
from core import actions, cabinet, notify
from core.paths import DEMO_DIR

A = Agent()


def _scan(user, fname, answers):
    t = str(uuid.uuid4())
    r = A.run("household", t, {"actor": user, "image": (DEMO_DIR / "labels" / fname).read_bytes(),
                               "filename": fname, "attempt": 1, "trace": []})
    pauses = []
    while r["waiting_for"]:
        pauses.append(r["waiting_for"]["type"])
        r = A.run("household", t, resume=answers[len(pauses) - 1](r["waiting_for"]))
    return r, pauses


confirm = lambda w: {"action": "confirm", "batch": w["fields"]["batch_number"]}


def test_flagged_label_pauses_for_confirmation_and_report_approval(users):
    r, pauses = _scan(users["home"], "1_cefixime_flagged.jpg", [confirm, lambda w: {"approve": False}])
    assert pauses == ["confirm_batch", "approve_report"]
    assert r["state"]["result"]["verdict"] == "FLAGGED"
    assert "pharmacist or doctor" in r["state"]["explanation"]["advice"]
    assert r["state"]["report"]["status"] == "rejected"          # nothing sent without approval
    assert r["state"]["image"] == b""                             # photo dropped after reading


def test_clear_label_is_saved_without_extra_pauses(users):
    r, pauses = _scan(users["home"], "2_paracetamol_clear.jpg", [confirm])
    assert pauses == ["confirm_batch"] and r["state"]["result"]["verdict"] == "CLEAR"


def test_unreadable_photo_asks_for_retake(users):
    r, pauses = _scan(users["home"], "5_cefixime_blurry.jpg", [])
    assert pauses == [] and r["state"]["status"] == "retake"


def test_stock_agent_drafts_returns_and_waits_for_pharmacist(users):
    df = pd.read_csv(DEMO_DIR / "inventory_sunrise_pharmacy_demo.csv")
    t = str(uuid.uuid4())
    r = A.run("stock", t, {"actor": users["pharm"], "rows": df.to_dict("records"), "trace": []})
    w = r["waiting_for"]
    assert w["type"] == "approve_stock_actions" and w["plan"]["flagged_ids"]
    assert all(a["status"] == "draft" for a in actions.list_actions(users["pharm"]))
    r = A.run("stock", t, resume={"quarantine_ids": w["plan"]["flagged_ids"],
                                  "approve_action_ids": [d["action_id"] for d in w["drafts"]], "reject_action_ids": []})
    assert r["done"] and "compliance report" in r["state"]["report"]["markdown"].lower()


def test_recheck_notifies_when_saved_medicine_appears_in_new_month(users):
    from conftest import TMP
    from core import ingest
    cabinet.add(users["home"], "Paracetamol Tablets IP 650 mg", "SAVED-ZZ9", "Demo", "2027", "CLEAR", None, None)
    files = [f for f in ingest.list_ingests() if f["source_file"] == "2026-08_central.pdf"]
    if not files:  # not yet ingested by another test
        r = ingest.ingest_file(users["admin"], TMP / "inbox" / "2026-08_central.pdf")
        files = [{"id": r["ingest_id"]}]
    cabinet.add(users["home"], "Amoxicillin and Potassium Clavulanate Tablets", "GBR1240", "Brooks", "2028",
                "CLEAR", None, None)
    from core.recheck import recheck_all
    ingest.approve(users["admin"], files[0]["id"], run_recheck=False)
    summary = recheck_all("test")
    assert summary["newly_flagged"] >= 1
    assert any("GBR1240" in n["message"] for n in notify.for_actor(users["home"]))

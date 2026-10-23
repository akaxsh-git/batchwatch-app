import pandas as pd
import pytest

from core import audit, cabinet, ingest, stock
from core.db import session


def _last(action):
    with session() as con:
        return con.execute("SELECT * FROM audit_log WHERE action=? ORDER BY id DESC LIMIT 1", (action,)).fetchone()


def test_pharmacist_cannot_approve_alert_data_and_attempt_is_logged(users):
    with pytest.raises(PermissionError):
        ingest.approve(users["pharm"], 1)
    row = _last("denied:approve_ingest")
    assert row and row["status"] == "denied" and row["actor"] == users["pharm"]["name"]


def test_household_cannot_check_pharmacy_stock(users):
    with pytest.raises(PermissionError):
        stock.check_inventory(users["home"], pd.DataFrame({"batch": ["X1"]}))


def test_pharmacists_only_see_their_own_organisation(users):
    stock.check_inventory(users["pharm"], pd.DataFrame({"product": ["A"], "batch": ["AAA111"]}))
    stock.check_inventory(users["pharm2"], pd.DataFrame({"product": ["B"], "batch": ["BBB222"]}))
    assert stock.get_inventory(users["pharm"]).batch.tolist() == ["AAA111"]
    assert stock.get_inventory(users["pharm2"]).batch.tolist() == ["BBB222"]
    assert all(r["org"] == users["pharm"]["org"] for r in audit.fetch(users["pharm"]))


def test_every_tool_call_is_audited(users):
    before = len(audit.fetch(users["admin"], limit=100000))
    stock.check_inventory(users["pharm"], pd.DataFrame({"product": ["A"], "batch": ["CCC333"]}))
    cabinet.add(users["home"], "X", "DDD444", "Y", "2027", "CLEAR", None, None)
    assert len(audit.fetch(users["admin"], limit=100000)) == before + 2
    assert _last("tool:check_inventory")["org"] == users["pharm"]["org"]

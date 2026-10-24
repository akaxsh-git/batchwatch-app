"""Tests for the new landing/login flow, session state management, and RBAC enforcement."""
import pytest
import streamlit as st

import ui
from core import audit, auth, db, ingest, stock


def test_actor_returns_none_when_unauthenticated():
    st.session_state.clear()
    assert ui.actor() is None


def test_login_and_logout_audit_logging():
    st.session_state.clear()
    # Mock st.rerun to prevent script termination during tests
    st.rerun = lambda: None

    # Sign in as Meera
    ui.login("Meera (Household)")
    assert st.session_state.get("user") == "Meera (Household)"
    actor = ui.actor()
    assert actor is not None
    assert actor["role"] == "household"

    # Verify auth:login is in the audit log
    logs = audit.fetch(actor, limit=5)
    login_events = [e for e in logs if e["action"] == "auth:login"]
    assert len(login_events) >= 1
    assert login_events[0]["actor"] == "Meera (Household)"
    assert login_events[0]["status"] == "ok"

    # Sign out
    ui.logout()
    assert "user" not in st.session_state
    assert ui.actor() is None

    # Verify auth:logout is in the audit log
    admin_user = db.get_user("Priya (Compliance Admin)")
    all_logs = audit.fetch(admin_user, limit=5)
    logout_events = [e for e in all_logs if e["action"] == "auth:logout"]
    assert len(logout_events) >= 1
    assert logout_events[0]["actor"] == "Meera (Household)"


def test_demo_step_7_ravi_cannot_approve_alert_data():
    """Demo step 7: Pharmacist (Ravi) attempts an admin-only action, is blocked and logged as denied."""
    ravi = db.get_user("Ravi (Pharmacist)")
    assert ravi["role"] == "pharmacist"

    with pytest.raises(PermissionError):
        ingest.approve(ravi, 1)

    # Check audit log for denied attempt
    logs = audit.fetch(ravi, limit=5)
    denied_events = [e for e in logs if e["action"] == "denied:approve_ingest"]
    assert len(denied_events) >= 1
    assert denied_events[0]["status"] == "denied"
    assert denied_events[0]["actor"] == ravi["name"]


def test_household_cannot_check_pharmacy_stock():
    """Household (Meera) attempts pharmacist action, blocked by backend."""
    meera = db.get_user("Meera (Household)")
    assert meera["role"] == "household"

    import pandas as pd
    with pytest.raises(PermissionError):
        stock.check_inventory(meera, pd.DataFrame({"batch": ["TEST1234"]}))

    logs = audit.fetch(meera, limit=5)
    denied_events = [e for e in logs if e["action"] == "denied:check_stock"]
    assert len(denied_events) >= 1
    assert denied_events[0]["status"] == "denied"


def test_unauthenticated_actor_has_no_permissions():
    """An unauthenticated actor dictionary cannot perform any action."""
    empty_actor = {}
    assert auth.can(empty_actor, "scan_label") is False
    assert auth.can(empty_actor, "check_stock") is False
    assert auth.can(empty_actor, "approve_ingest") is False

    with pytest.raises(PermissionError):
        auth.require(empty_actor, "view_alerts")

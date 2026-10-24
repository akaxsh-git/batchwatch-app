"""Landing and role-selection page for BatchWatch.

Shown when no active persona is signed in.
Allows choosing between Household, Pharmacist, and Compliance Admin roles.
"""
import streamlit as st

import ui
from core import audit, db


def do_login(user_name: str):
    """Sign in as a demo persona, write to audit log, and rerun."""
    u = db.get_user(user_name)
    st.session_state["user"] = user_name
    audit.log(u, "auth:login", status="ok", output={"role": u["role"], "org": u.get("org")})
    st.rerun()


# Page header
ui.setup_page("💊 BatchWatch")
st.markdown(
    "#### Autonomous compliance & drug-quality alert checking for India"
)
st.caption(
    "BatchWatch monitors India's monthly CDSCO lists of Not of Standard Quality (NSQ) and spurious "
    "medicine batches. Select a role below to enter the application."
)

st.write("")

c1, c2, c3 = st.columns(3)

# ── 1. Household Role Card ───────────────────────────────────────────────────
with c1:
    with st.container(border=True):
        st.markdown("### 📷 Household")
        st.markdown("**Check Medicines at Home**")
        st.write(
            "Photograph a medicine strip or carton to verify its batch number against official CDSCO alerts. "
            "Get plain-language explanations in English, Hindi, or Kannada and monitor saved items in your cabinet."
        )
        st.caption("👤 Persona: **Meera (Household)**")
        st.write("")
        if st.button("Enter as Meera (Household)", key="btn_meera", type="primary", use_container_width=True):
            do_login("Meera (Household)")

# ── 2. Pharmacist Role Card ──────────────────────────────────────────────────
with c2:
    with st.container(border=True):
        st.markdown("### 🏥 Pharmacist")
        st.markdown("**Check Pharmacy Inventory**")
        st.write(
            "Upload stock CSV files to check hundreds of pharmacy lines in seconds. "
            "Quarantine flagged lots, approve AI-drafted supplier return requests, and export audit-ready reports."
        )
        st.caption("👤 Persona: **Ravi (Pharmacist)** · *Sunrise Pharmacy*")
        st.write("")
        if st.button("Enter as Ravi (Pharmacist)", key="btn_ravi", type="primary", use_container_width=True):
            do_login("Ravi (Pharmacist)")

# ── 3. Compliance Admin Role Card ────────────────────────────────────────────
with c3:
    with st.container(border=True):
        st.markdown("### 🗂️ Compliance Admin")
        st.markdown("**Manage Official Alert Data**")
        st.write(
            "Review and ingest incoming monthly CDSCO alert PDFs. Inspect automated "
            "gap-free (1..N) validation checks, approve live data, and trigger automated re-checks across all saved stock."
        )
        st.caption("👤 Persona: **Priya (Compliance Admin)**")
        st.write("")
        if st.button("Enter as Priya (Compliance Admin)", key="btn_priya", type="primary", use_container_width=True):
            do_login("Priya (Compliance Admin)")

# ── Honest security note ─────────────────────────────────────────────────────
st.divider()
st.markdown(
    "<div style='font-size: 0.84rem; opacity: 0.75; line-height: 1.5; text-align: center;'>"
    "<b>ℹ️ Notice:</b> This landing page is a demonstration role picker mapping directly to pre-configured database personas. "
    "Production deployments require enterprise authentication (OAuth 2.0 / SAML SSO or securely hashed credentials). "
    "Role-based access permissions are enforced strictly at the backend layer."
    "</div>",
    unsafe_allow_html=True,
)

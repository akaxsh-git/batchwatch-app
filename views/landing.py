"""Landing and role-selection page for BatchWatch.

Shown when no active persona is signed in.
Allows choosing between Household, Pharmacist, and Compliance Admin roles.
"""
import streamlit as st

import ui
from core import audit, db

# Setup page styling without sidebar pollution
ui.setup_page("💊 BatchWatch")

st.markdown(
    "<div style='font-size: 1.15rem; opacity: 0.85; margin-top: -10px; margin-bottom: 24px; line-height: 1.5;'>"
    "Autonomous compliance & quality checking for India's monthly CDSCO drug-quality alerts."
    "</div>",
    unsafe_allow_html=True,
)

st.markdown(
    """
<style>
.role-card {
    border-radius: 12px;
    padding: 24px 20px 20px;
    border: 1.5px solid rgba(148, 163, 184, 0.25);
    background: rgba(148, 163, 184, 0.05);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-height: 380px;
    margin-bottom: 16px;
    transition: transform 0.15s ease, border-color 0.15s ease;
}
.role-card:hover {
    border-color: #3B82F6;
    transform: translateY(-2px);
}
.role-icon {
    font-size: 2.4rem;
    margin-bottom: 8px;
}
.role-title {
    font-size: 1.2rem;
    font-weight: 700;
    margin-bottom: 4px;
    color: var(--text-color);
}
.role-tagline {
    font-size: 0.85rem;
    font-weight: 600;
    color: #3B82F6;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 12px;
}
.role-desc {
    font-size: 0.90rem;
    line-height: 1.55;
    color: var(--text-color);
    opacity: 0.85;
    flex-grow: 1;
    margin-bottom: 16px;
}
.role-persona {
    font-size: 0.78rem;
    background: rgba(148, 163, 184, 0.12);
    border: 1px solid rgba(148, 163, 184, 0.2);
    padding: 3px 8px;
    border-radius: 6px;
    margin-bottom: 14px;
    color: var(--text-color);
    opacity: 0.90;
}
</style>
""",
    unsafe_allow_html=True,
)

c1, c2, c3 = st.columns(3)

# ── 1. Household Role Card ───────────────────────────────────────────────────
with c1:
    st.markdown(
        """
        <div class="role-card">
            <div>
                <div class="role-icon">📷</div>
                <div class="role-title">Household</div>
                <div class="role-tagline">Check My Medicines</div>
                <div class="role-desc">
                    Photograph a medicine strip or carton to check its batch number against official CDSCO alerts.
                    Receive grounded, plain-language explanations in English, Hindi, or Kannada, and monitor
                    saved items in your personal medicine cabinet with automated monthly re-checks.
                </div>
                <div class="role-persona">👤 Demo user: <b>Meera (Household)</b></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Enter as Meera (Household)", key="login_home", type="primary", use_container_width=True):
        ui.login("Meera (Household)")

# ── 2. Pharmacist Role Card ──────────────────────────────────────────────────
with c2:
    st.markdown(
        """
        <div class="role-card">
            <div>
                <div class="role-icon">🏥</div>
                <div class="role-title">Pharmacist</div>
                <div class="role-tagline">Check Pharmacy Stock</div>
                <div class="role-desc">
                    Upload an inventory CSV to check hundreds of pharmacy lines in seconds.
                    Review flagged and OCR-lookalike batches, quarantine affected stock, approve
                    AI-drafted supplier return requests, and export verified compliance audit reports.
                </div>
                <div class="role-persona">👤 Demo user: <b>Ravi (Pharmacist)</b> · Sunrise Pharmacy</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Enter as Ravi (Pharmacist)", key="login_pharm", type="primary", use_container_width=True):
        ui.login("Ravi (Pharmacist)")

# ── 3. Compliance Admin Role Card ────────────────────────────────────────────
with c3:
    st.markdown(
        """
        <div class="role-card">
            <div>
                <div class="role-icon">🗂️</div>
                <div class="role-title">Compliance Admin</div>
                <div class="role-tagline">Manage Alert Data</div>
                <div class="role-desc">
                    Review and parse incoming monthly CDSCO alert PDFs. Inspect automated
                    serial-number validation (1..N gap checks) and approve verified files to go live.
                    Approval automatically triggers system-wide re-checks across all saved inventories and cabinets.
                </div>
                <div class="role-persona">👤 Demo user: <b>Priya (Compliance Admin)</b></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Enter as Priya (Compliance Admin)", key="login_admin", type="primary", use_container_width=True):
        ui.login("Priya (Compliance Admin)")

# ── Demo disclaimer note ─────────────────────────────────────────────────────
st.divider()
st.markdown(
    "<div style='font-size: 0.82rem; opacity: 0.70; line-height: 1.5; text-align: center;'>"
    "<b>ℹ️ Notice:</b> This landing page is a demonstration role picker mapping directly to pre-configured database personas. "
    "Production deployments require enterprise authentication (OAuth 2.0 / SAML SSO or securely hashed credentials). "
    "Role-based permissions are enforced strictly at the backend layer."
    "</div>",
    unsafe_allow_html=True,
)

"""Shared UI helpers for the Streamlit app."""
import html
import os
from pathlib import Path

import streamlit as st

from agent import llm, translate
from agent.graphs import Agent
from core import db, ingest

# ---------------------------------------------------------------------------
# Verdict colour tokens
# High contrast in both light and dark themes.
# ---------------------------------------------------------------------------
COLORS = {
    "FLAGGED":  ("#DC2626", "#FFFFFF"),
    "POSSIBLE": ("#D97706", "#FFFFFF"),
    "CLEAR":    ("#15803D", "#FFFFFF"),
    "RETAKE":   ("#4B5563", "#FFFFFF"),
}

# Non-negotiable rule: verdict labels stay deterministic and unchanged in English.
LABELS = {
    "FLAGGED": "FLAGGED",
    "POSSIBLE": "POSSIBLE",
    "CLEAR": "NOT IN ALERTS",
    "RETAKE": "UNREADABLE",
}

_CARD_BORDER = {
    "FLAGGED":  "#DC2626",
    "POSSIBLE": "#D97706",
    "CLEAR":    "#15803D",
    "RETAKE":   "#4B5563",
}

_CARD_TINT = {
    "FLAGGED":  "rgba(220, 38, 38, 0.08)",
    "POSSIBLE": "rgba(217, 119, 6, 0.08)",
    "CLEAR":    "rgba(21, 128, 61, 0.08)",
    "RETAKE":   "rgba(75, 85, 99, 0.08)",
}

# ---------------------------------------------------------------------------
# Global CSS: Clean, clinical, professional design system
# Uses Streamlit's official CSS custom properties (var(--text-color), etc.)
# so that all cards, chips, and text adapt cleanly to both Light and Dark themes.
# ---------------------------------------------------------------------------
CSS = """
<style>
/* ── Page-width cap (1250px) ─────────────────────────────────────────── */
.block-container {
    max-width: 1250px !important;
    padding-top: 1.5rem !important;
    padding-bottom: 2.5rem !important;
}

/* ── Verdict pill badge ───────────────────────────────────────────────── */
.pill {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 9999px;
    font-weight: 700;
    font-size: 0.75rem;
    letter-spacing: 0.6px;
    text-transform: uppercase;
    vertical-align: middle;
    line-height: 1.6;
}

/* ── Professional Verdict Card Layout ────────────────────────────────── */
.vcard {
    border-radius: 12px;
    padding: 22px 24px 20px;
    margin: 12px 0 20px;
    border-width: 1.5px;
    border-style: solid;
    color: var(--text-color);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}
.vcard h3 {
    margin: 10px 0 6px;
    font-size: 1.15rem;
    font-weight: 700;
    letter-spacing: -0.2px;
    color: var(--text-color);
}
.vcard-summary {
    font-size: 0.94rem;
    font-weight: 500;
    line-height: 1.55;
    margin: 0 0 14px;
    color: var(--text-color);
    opacity: 0.95;
}

/* ── Patient Explanation Block ───────────────────────────────────────── */
.vcard-patient-box {
    border-radius: 8px;
    padding: 14px 16px;
    margin: 12px 0;
    line-height: 1.6;
    font-size: 0.92rem;
    background: rgba(148, 163, 184, 0.08);
    border: 1px solid rgba(148, 163, 184, 0.2);
    color: var(--text-color);
}
.vcard-patient-box p {
    margin: 0 0 8px;
}
.vcard-patient-box p:last-child {
    margin-bottom: 0;
}
.vcard-advice {
    font-weight: 600;
    margin-top: 8px !important;
}
.vcard-disclaimer {
    font-size: 0.78rem;
    margin-top: 10px !important;
    opacity: 0.75;
}
.vcard-notice-tag {
    display: inline-block;
    font-size: 0.75rem;
    padding: 2px 8px;
    border-radius: 4px;
    margin-bottom: 8px;
    font-style: italic;
    background: rgba(217, 119, 6, 0.15);
    color: #D97706;
    border: 1px solid rgba(217, 119, 6, 0.3);
}

/* ── Technical Regulatory Dossier Sub-Panel ──────────────────────────── */
.vcard-tech-box {
    border-radius: 8px;
    padding: 14px 16px;
    margin-top: 14px;
    font-size: 0.86rem;
    line-height: 1.55;
    background: rgba(148, 163, 184, 0.06);
    border: 1px solid rgba(148, 163, 184, 0.2);
    color: var(--text-color);
}
.vcard-tech-header {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    opacity: 0.70;
    margin-bottom: 8px;
    color: var(--text-color);
}
.vcard-tech-row {
    margin: 4px 0;
    color: var(--text-color);
}

/* ── Monospace citation chip ─────────────────────────────────────────── */
.cite {
    font-family: ui-monospace, Menlo, "Cascadia Code", monospace;
    font-size: 0.80rem;
    padding: 2px 8px;
    border-radius: 5px;
    background: rgba(148, 163, 184, 0.15);
    color: var(--text-color);
    border: 1px solid rgba(148, 163, 184, 0.25);
}

/* ── Muted text ───────────────────────────────────────────────────────── */
.muted {
    opacity: 0.70;
    font-size: 0.82rem;
    color: var(--text-color);
}

/* ── Agent step trace ─────────────────────────────────────────────────── */
.step {
    margin: 4px 0;
    font-size: 0.86rem;
    opacity: 0.85;
    color: var(--text-color);
}

/* ── Clean Empty States ───────────────────────────────────────────────── */
.empty-state {
    text-align: center;
    padding: 2.2rem 1.2rem;
    border-radius: 10px;
    border: 1px dashed rgba(148, 163, 184, 0.35);
    margin: 1.2rem 0;
    color: var(--text-color);
    opacity: 0.75;
}
.empty-state .es-icon {
    font-size: 2rem;
    display: block;
    margin-bottom: 0.5rem;
}

/* ── Responsive adjustments ───────────────────────────────────────────── */
@media (max-width: 640px) {
    .vcard { padding: 16px 16px 14px; }
    .block-container {
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }
}
</style>
"""


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def setup_page(title: str):
    """Inject global theme-adaptive CSS and render page title."""
    st.markdown(CSS, unsafe_allow_html=True)
    st.title(title)


@st.cache_resource
def get_agent() -> Agent:
    return Agent()


def ensure_db():
    """Initialize DB and automatically bootstrap on Streamlit Cloud if empty."""
    db.init_db()
    db.seed_users()

    # Do not auto-bootstrap during automated test runs
    if os.getenv("PYTEST_CURRENT_TEST"):
        return

    s = ingest.stats()
    if not s.get("live_rows"):
        admin = db.get_user("Priya (Compliance Admin)")
        if admin:
            from core.paths import ALERTS_DIR
            for pdf in sorted(Path(ALERTS_DIR).glob("*.pdf")):
                if pdf.name not in ingest.known_files():
                    r = ingest.ingest_file(admin, pdf)
                    if r.get("validation") == "passed":
                        ingest.approve(admin, r["ingest_id"], run_recheck=False)


def actor() -> dict:
    name = st.session_state.get("user")
    return db.get_user(name) if name else None


def current_lang() -> str:
    """Return the currently selected language code (en, hi, kn)."""
    return st.session_state.get("lang", "en")


def pill(verdict: str) -> str:
    """Return an HTML pill badge for a verdict key."""
    bg, fg = COLORS.get(verdict, ("#64748B", "#fff"))
    label = LABELS.get(verdict, verdict)
    return f'<span class="pill" style="background:{bg};color:{fg}">{label}</span>'


def verdict_card(result: dict, explanation: dict = None):
    """Render a clean, clinical-grade verdict card with separated patient and technical sections."""
    v = result["verdict"]
    top = result["matches"][0] if result.get("matches") else None
    lang = current_lang()

    border_col = _CARD_BORDER.get(v, "#64748B")
    tint = _CARD_TINT.get(v, "rgba(100,116,139,0.08)")

    title_text = translate.get_card_title(v, lang)
    summary_text = translate.get_verdict_summary(v, lang)

    body = ""

    if v == "FLAGGED" and top:
        # ── 1. Patient Explanation Section
        patient_content = ""
        if explanation:
            t_expl = translate.translate_explanation(top, explanation, lang)
            if t_expl.get("notice"):
                patient_content += f"<span class='vcard-notice-tag'>{html.escape(t_expl['notice'])}</span>"
            patient_content += f"<p>{html.escape(t_expl['text'])}</p>"
            patient_content += f"<p class='vcard-advice'>{html.escape(t_expl['advice'])}</p>"
            if t_expl.get("disclaimer"):
                patient_content += f"<p class='vcard-disclaimer'>⚠️ {html.escape(t_expl['disclaimer'])}</p>"
        else:
            patient_content += f"<p>{html.escape(summary_text)}</p>"

        body += f"<div class='vcard-patient-box'>{patient_content}</div>"

        # ── 2. Technical Regulatory Dossier Sub-Panel
        failure = (top.get("failure_reason") or top.get("remarks") or "")[:300]
        alert_info = f"{html.escape(top.get('alert_month', ''))} {html.escape(top.get('list_type', ''))} list"
        if top.get("tested_by"):
            alert_info += f" · Tested by: {html.escape(top['tested_by'])}"

        multi_flag = ""
        if result.get("times_flagged", 0) > 1:
            multi_flag = (
                f"<div class='vcard-tech-row' style='color:#F59E0B;font-weight:600;'>"
                f"⚠️ Note: This batch was flagged in {result['times_flagged']} separate CDSCO alerts.</div>"
            )

        body += (
            f"<div class='vcard-tech-box'>"
            f"<div class='vcard-tech-header'>Official CDSCO Alert Dossier</div>"
            f"<div class='vcard-tech-row'><b>Medicine / Product:</b> {html.escape(top.get('product', ''))}</div>"
            f"<div class='vcard-tech-row'><b>Batch on alert:</b> <code>{html.escape(top.get('batch', ''))}</code></div>"
            f"<div class='vcard-tech-row'><b>Alert record:</b> {alert_info}</div>"
            f"<div class='vcard-tech-row'><b>Lab finding (original English):</b> {html.escape(failure)}</div>"
            f"{multi_flag}"
            f"<div class='vcard-tech-row' style='margin-top:6px;'><b>Source citation:</b> <span class='cite'>{html.escape(top.get('citation', ''))}</span></div>"
            f"</div>"
        )

    elif v == "POSSIBLE" and top:
        body += (
            f"<div class='vcard-tech-box'>"
            f"<div class='vcard-tech-header'>Closest Listed Batch</div>"
            f"<div class='vcard-tech-row'><b>Listed batch:</b> <code>{html.escape(top['batch'])}</code> ({html.escape(top['product'])})</div>"
            f"<div class='vcard-tech-row'><b>Alert source:</b> <span class='cite'>{html.escape(top['citation'])}</span></div>"
            f"</div>"
        )

    elif v == "CLEAR":
        clear_text = translate.get_clear_details(lang)
        body += f"<div class='vcard-patient-box'><p>{html.escape(clear_text)}</p></div>"

    card_html = (
        f"<div class='vcard' style='border-color:{border_col};background:{tint};'>"
        f"{pill(v)}"
        f"<h3>{html.escape(title_text)}</h3>"
        f"<p class='vcard-summary'>{html.escape(summary_text)}</p>"
        f"{body}"
        f"</div>"
    )
    st.markdown(card_html, unsafe_allow_html=True)


def show_trace(trace: list, expanded=False):
    """Render the agent step trace inside an expander."""
    with st.expander(f"Agent steps ({len(trace)})", expanded=expanded):
        for i, t in enumerate(trace, 1):
            st.markdown(
                f"<div class='step'>{i}. {html.escape(t)}</div>",
                unsafe_allow_html=True,
            )


def empty_state(icon: str, message: str):
    """Render a centred empty-state callout."""
    st.markdown(
        f"<div class='empty-state'>"
        f"<span class='es-icon'>{icon}</span>"
        f"{html.escape(message)}"
        f"</div>",
        unsafe_allow_html=True,
    )


def login(user_name: str):
    """Sign in as a demo persona, write to audit log, and rerun."""
    u = db.get_user(user_name)
    st.session_state["user"] = user_name
    from core import audit
    audit.log(u, "auth:login", status="ok", output={"role": u["role"], "org": u.get("org")})
    st.rerun()


def logout():
    """Sign out the current user, write to audit log, and return to landing page."""
    a = actor()
    if a:
        from core import audit
        audit.log(a, "auth:logout", status="ok", output={"role": a["role"], "org": a.get("org")})
    st.session_state.pop("user", None)
    st.rerun()


def sidebar():
    if "lang" not in st.session_state:
        st.session_state["lang"] = "en"
    a = actor()
    if not a:
        return None

    with st.sidebar:
        st.markdown("### 💊 BatchWatch")
        st.caption("Agentic compliance for CDSCO drug-quality alerts")

        # Current user badge and switch user button (replacing old dropdown)
        st.markdown(f"**Signed in as:**  \n**{html.escape(a['name'])}**")
        st.markdown(
            f"{pill(a['role'])} " + (f"· <span class='muted'>{html.escape(a['org'])}</span>" if a.get("org") else ""),
            unsafe_allow_html=True,
        )
        if st.button("🔄 Switch user / Sign out", use_container_width=True):
            logout()

        st.divider()
        st.selectbox(
            "Language / भाषा / ಭಾಷೆ",
            list(translate.LANGUAGES.keys()),
            key="lang",
            format_func=lambda code: translate.LANGUAGES[code],
        )

        s = ingest.stats()
        st.caption(
            f"**Live alert data:** {s['live_rows'] or 0} batches · "
            f"{s['first'] or '–'} → {s['last'] or '–'}"
        )
        if s["pending_files"]:
            st.caption(f"⏳ {s['pending_files']} alert file(s) waiting for admin approval")
        m = llm.mode()
        st.caption(
            "**AI:** " + (
                f"Gemini ({llm.MODEL})" if m == "gemini" else "offline fallback (no API key)"
            )
        )
        st.caption(
            "Role-based access is enforced in the backend; every action is in the audit log."
        )
    return a

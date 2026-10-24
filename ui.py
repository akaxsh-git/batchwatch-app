"""Shared UI helpers for the Streamlit app."""
import html

import streamlit as st

from agent import llm, translate
from agent.graphs import Agent
from core import db, ingest

# ---------------------------------------------------------------------------
# Verdict colour tokens
# Each entry: (pill_bg, pill_fg, card_border, card_bg_alpha_overlay)
# We use the same pill colours in light and dark; the card backgrounds are
# semi-transparent overlays applied via CSS rgba so they adapt to the theme.
# ---------------------------------------------------------------------------
COLORS = {
    "FLAGGED":  ("#DC2626", "#FFFFFF"),
    "POSSIBLE": ("#D97706", "#FFFFFF"),
    "CLEAR":    ("#15803D", "#FFFFFF"),
    "RETAKE":   ("#4B5563", "#FFFFFF"),
}

# Human-readable label for each verdict key used in the UI
# Non-negotiable rule: verdict labels stay deterministic and unchanged in English.
LABELS = {
    "FLAGGED": "FLAGGED",
    "POSSIBLE": "POSSIBLE",
    "CLEAR": "NOT IN ALERTS",
    "RETAKE": "UNREADABLE",
}

# Card left-border colours (visible on both themes)
_CARD_BORDER = {
    "FLAGGED":  "#DC2626",
    "POSSIBLE": "#D97706",
    "CLEAR":    "#15803D",
    "RETAKE":   "#4B5563",
}

# Card background tint: a very low-opacity rgba that works on both dark and
# light backgrounds because it blends with whatever the theme's base is.
_CARD_TINT = {
    "FLAGGED":  "rgba(220, 38, 38, 0.08)",
    "POSSIBLE": "rgba(217, 119, 6, 0.08)",
    "CLEAR":    "rgba(21, 128, 61, 0.08)",
    "RETAKE":   "rgba(75, 85, 99, 0.08)",
}

# ---------------------------------------------------------------------------
# Global CSS — all colours reference CSS custom properties set by Streamlit
# from the active theme, so they adapt to both light and dark.
# ---------------------------------------------------------------------------
CSS = """
<style>
/* ── Page-width cap ───────────────────────────────────────────────────── */
.block-container {
    max-width: 1250px !important;
    padding-top: 1.75rem !important;
    padding-bottom: 3rem !important;
}

/* ── Verdict pill badge ───────────────────────────────────────────────── */
.pill {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 14px;
    font-weight: 700;
    font-size: 0.75rem;
    letter-spacing: 0.6px;
    text-transform: uppercase;
    vertical-align: middle;
    line-height: 1.6;
}

/* ── Verdict card ─────────────────────────────────────────────────────── */
.vcard {
    border-radius: 10px;
    padding: 18px 22px 16px;
    margin: 8px 0 16px;
    border-width: 1px;
    border-style: solid;
}
.vcard h3 {
    margin: 6px 0 4px;
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--text-color);
}
.vcard-summary {
    font-size: 0.88rem;
    color: var(--text-color);
    opacity: 0.90;
    margin: 0 0 10px;
    line-height: 1.5;
}

/* ── Inline citation monospace chip ──────────────────────────────────── */
.cite {
    font-family: ui-monospace, Menlo, "Cascadia Code", monospace;
    font-size: 0.80rem;
    background: rgba(148, 163, 184, 0.15);
    padding: 1px 7px;
    border-radius: 5px;
    border: 1px solid rgba(148, 163, 184, 0.2);
}

/* ── Muted / secondary text ──────────────────────────────────────────── */
.muted {
    opacity: 0.65;
    font-size: 0.82rem;
}

/* ── Agent trace step ─────────────────────────────────────────────────── */
.step {
    margin: 3px 0;
    font-size: 0.86rem;
    opacity: 0.85;
}

/* ── Empty-state callout ─────────────────────────────────────────────── */
.empty-state {
    text-align: center;
    padding: 2rem 1rem;
    border-radius: 10px;
    border: 1px dashed rgba(148, 163, 184, 0.35);
    color: var(--text-color);
    opacity: 0.65;
    margin: 1rem 0;
}
.empty-state .es-icon {
    font-size: 2rem;
    display: block;
    margin-bottom: 0.4rem;
}

/* ── Mobile tweaks ───────────────────────────────────────────────────── */
@media (max-width: 640px) {
    .vcard { padding: 14px 14px 12px; }
    .block-container {
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
    }
}
</style>
"""


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def setup_page(title: str):
    """Inject global CSS and render the page title."""
    st.markdown(CSS, unsafe_allow_html=True)
    st.title(title)


@st.cache_resource
def get_agent() -> Agent:
    return Agent()


def ensure_db():
    db.init_db()
    db.seed_users()


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
    """Render a styled verdict card with summary text, full detail, and multilingual explanation."""
    v = result["verdict"]
    top = result["matches"][0] if result.get("matches") else None
    lang = current_lang()

    border_col = _CARD_BORDER.get(v, "#64748B")
    tint = _CARD_TINT.get(v, "rgba(100,116,139,0.08)")

    # Plain-language explanation under verdict title (multilingual)
    summary = translate.get_verdict_summary(v, lang)

    # Card heading text
    title_text = {
        "FLAGGED":  "This batch appears in a published CDSCO drug-quality alert",
        "POSSIBLE": "Possible match — please check the batch number on the pack",
        "CLEAR":    "Not found in published CDSCO alerts",
        "RETAKE":   "Batch number could not be read",
    }.get(v, v)

    body = ""

    if v == "FLAGGED" and top:
        body += (
            f"<p><b>{html.escape(top['product'])}</b> · "
            f"batch <b>{html.escape(top['batch'])}</b> · "
            f"{html.escape(top['alert_month'])} {top['list_type']} list · "
            f"tested by {html.escape(top['tested_by'] or '')}</p>"
        )

        if explanation:
            t_expl = translate.translate_explanation(top, explanation, lang)
            body += (
                f"<p>{html.escape(t_expl['text'])}</p>"
                f"<p><b>{html.escape(t_expl['advice'])}</b></p>"
            )
            if t_expl.get("notice"):
                body += f"<p class='muted'><em>{html.escape(t_expl['notice'])}</em></p>"
            if t_expl.get("disclaimer"):
                body += (
                    f"<p class='muted' style='font-size:0.78rem;'>"
                    f"⚠️ {html.escape(t_expl['disclaimer'])}</p>"
                )

        failure = (top["failure_reason"] or top.get("remarks") or "")[:300]
        if failure:
            prefix = "Lab finding (original English):" if lang != "en" else "Lab finding:"
            body += f"<p class='muted'>{prefix} {html.escape(failure)}</p>"

        if result.get("times_flagged", 0) > 1:
            body += (
                f"<p>⚠️ This batch was flagged in "
                f"<b>{result['times_flagged']}</b> separate alerts.</p>"
            )
        body += f"<p>Source: <span class='cite'>{html.escape(top['citation'])}</span></p>"

    elif v == "POSSIBLE" and top:
        body += (
            f"<p>Closest listed batch: <b>{html.escape(top['batch'])}</b> "
            f"({html.escape(top['product'])}) · "
            f"<span class='cite'>{html.escape(top['citation'])}</span></p>"
        )

    elif v == "CLEAR":
        clear_text = translate.get_clear_details(lang)
        body += f"<p>{html.escape(clear_text)}</p>"

    card_html = (
        f"<div class='vcard' style='"
        f"border-color:{border_col};"
        f"background:{tint}'>"
        f"{pill(v)}"
        f"<h3>{html.escape(title_text)}</h3>"
        f"<p class='vcard-summary'>{html.escape(summary)}</p>"
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


def sidebar():
    users = db.list_users()
    names = [u["name"] for u in users]
    if "user" not in st.session_state:
        st.session_state["user"] = names[0]
    if "lang" not in st.session_state:
        st.session_state["lang"] = "en"

    with st.sidebar:
        st.markdown("### 💊 BatchWatch")
        st.caption("Agentic compliance for CDSCO drug-quality alerts")

        st.selectbox(
            "Signed in as (demo)", names, key="user",
            format_func=lambda n: f"{n} · {next(u['role'] for u in users if u['name'] == n)}",
        )
        a = actor()
        if a.get("org"):
            st.caption(f"Organisation: **{a['org']}**")

        st.selectbox(
            "Language / भाषा / ಭಾಷೆ",
            list(translate.LANGUAGES.keys()),
            key="lang",
            format_func=lambda code: translate.LANGUAGES[code],
        )

        s = ingest.stats()
        st.divider()
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

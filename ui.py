"""Shared UI helpers for the Streamlit app."""
import html

import streamlit as st

from agent import llm
from agent.graphs import Agent
from core import db, ingest

COLORS = {"FLAGGED": ("#B5523B", "#FFFFFF"), "POSSIBLE": ("#C8962E", "#FFFFFF"),
          "CLEAR": ("#5E7346", "#FFFFFF"), "RETAKE": ("#7A665A", "#FFFFFF")}
LABELS = {"FLAGGED": "FLAGGED", "POSSIBLE": "POSSIBLE", "CLEAR": "NOT IN ALERTS", "RETAKE": "UNREADABLE"}

CSS = """
<style>
.pill{display:inline-block;padding:2px 10px;border-radius:12px;font-weight:700;font-size:0.78rem;letter-spacing:.3px}
.card{border:1px solid #D9C7B4;border-radius:8px;padding:16px 18px;background:#FFFFFF;margin:6px 0 12px}
.card h3{margin:0 0 6px 0}
.cite{font-family:ui-monospace,Menlo,monospace;font-size:0.82rem;background:#F1E7DA;padding:1px 6px;border-radius:4px}
.muted{color:#7A665A}
.step{margin:2px 0}
</style>
"""


def setup_page(title: str):
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


def pill(verdict: str) -> str:
    bg, fg = COLORS.get(verdict, ("#999", "#fff"))
    return f'<span class="pill" style="background:{bg};color:{fg}">{LABELS.get(verdict, verdict)}</span>'


def verdict_card(result: dict, explanation: dict = None):
    v = result["verdict"]
    top = result["matches"][0] if result.get("matches") else None
    title = {"FLAGGED": "This batch appears in a CDSCO drug-quality alert",
             "POSSIBLE": "Possible match: please check the batch number on the pack",
             "CLEAR": "Not found in published CDSCO alerts",
             "RETAKE": "Batch number could not be read"}[v]
    body = ""
    if v == "FLAGGED" and top:
        body += f"<p><b>{html.escape(top['product'])}</b> · batch <b>{html.escape(top['batch'])}</b> · " \
                f"{html.escape(top['alert_month'])} {top['list_type']} list · tested by {html.escape(top['tested_by'] or '')}</p>"
        if explanation:
            body += f"<p>{html.escape(explanation['text'])}</p><p><b>{html.escape(explanation['advice'])}</b></p>"
        body += f"<p class='muted'>Lab finding: {html.escape((top['failure_reason'] or top.get('remarks') or '')[:300])}</p>"
        if result.get("times_flagged", 0) > 1:
            body += f"<p>⚠️ This batch was flagged in <b>{result['times_flagged']}</b> separate alerts.</p>"
        body += f"<p>Source: <span class='cite'>{html.escape(top['citation'])}</span></p>"
    elif v == "POSSIBLE" and top:
        body += f"<p>Closest listed batch: <b>{html.escape(top['batch'])}</b> ({html.escape(top['product'])}) · " \
                f"<span class='cite'>{html.escape(top['citation'])}</span></p>"
    elif v == "CLEAR":
        body += "<p>No published alert lists this batch. This is <b>not</b> a certificate of quality: only " \
                "sampled batches are tested. We'll re-check automatically when new alerts come out.</p>"
    st.markdown(f"<div class='card'>{pill(v)}<h3>{title}</h3>{body}</div>", unsafe_allow_html=True)


def show_trace(trace: list, expanded=False):
    with st.expander(f"Agent steps ({len(trace)})", expanded=expanded):
        for i, t in enumerate(trace, 1):
            st.markdown(f"<div class='step'>{i}. {html.escape(t)}</div>", unsafe_allow_html=True)


def sidebar():
    users = db.list_users()
    names = [u["name"] for u in users]
    if "user" not in st.session_state:
        st.session_state["user"] = names[0]
    with st.sidebar:
        st.markdown("### 💊 BatchWatch")
        st.caption("Agentic compliance for CDSCO drug-quality alerts")
        st.selectbox("Signed in as (demo)", names, key="user",
                     format_func=lambda n: f"{n} · {next(u['role'] for u in users if u['name']==n)}")
        a = actor()
        if a.get("org"):
            st.caption(f"Organisation: **{a['org']}**")
        s = ingest.stats()
        st.divider()
        st.caption(f"**Live alert data:** {s['live_rows'] or 0} batches · {s['first'] or '-'} → {s['last'] or '-'}")
        if s["pending_files"]:
            st.caption(f"⏳ {s['pending_files']} alert file(s) waiting for admin approval")
        m = llm.mode()
        st.caption("**AI:** " + (f"Gemini ({llm.MODEL})" if m == "gemini" else "offline fallback (no API key)"))
        st.caption("Role-based access is enforced in the backend; every action is in the audit log.")
    return a

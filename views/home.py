import calendar

import pandas as pd
import streamlit as st

import ui
from core import ingest, matcher, notify

ui.setup_page("BatchWatch")
a = ui.actor()
s = ingest.stats()

intro = {
    "admin": (
        "You review each month's CDSCO alert files before they go live. "
        "Nothing is used for matching until you approve it."
    ),
    "pharmacist": (
        f"Check **{a.get('org')}**'s stock against every published CDSCO alert, "
        "quarantine flagged batches, and approve supplier returns."
    ),
    "household": (
        "Photograph a medicine strip to check its batch against CDSCO's drug-quality alerts. "
        "Saved medicines are re-checked every month."
    ),
}
st.markdown(f"Signed in as **{a['name']}** ({a['role']}). {intro[a['role']]}")

# ── Key metrics ─────────────────────────────────────────────────────────────
fmt = lambda m: f"{calendar.month_abbr[int(m[5:7])]} {m[:4]}" if m else "–"

c1, c2, c3, c4 = st.columns(4)
c1.metric("Live alert batches", s["live_rows"] or 0)
c2.metric("Months covered", f"{fmt(s['first'])[:3]}–{fmt(s['last'])[:3]}" if s["first"] else "–")
c3.metric(
    "Central / State / Spurious",
    f"{s['by_type'].get('central', 0)} / {s['by_type'].get('state', 0)} / {s['by_type'].get('spurious', 0)}",
)
c4.metric("New / pending alert files", f"{len(ingest.scan_inbox())} / {s['pending_files']}")

# ── Notifications ────────────────────────────────────────────────────────────
st.subheader("Notifications")
notes = notify.for_actor(a)
if not notes:
    ui.empty_state(
        "🔔",
        "No notifications yet. You'll be told here when a re-check finds something new.",
    )
for n in notes[:10]:
    st.markdown(
        f"{ui.pill(n['verdict'])} {n['message']}  \n"
        f"<span class='muted'>{n['created_at']}</span>",
        unsafe_allow_html=True,
    )

# ── Quick batch lookup (admin / pharmacist only) ─────────────────────────────
if a["role"] in ("admin", "pharmacist"):
    st.subheader("Quick batch lookup")
    q = st.text_input("Batch number", placeholder="e.g. 25460922")
    if q:
        r = matcher.match(q)
        st.markdown(ui.pill(r["verdict"]), unsafe_allow_html=True)
        if r["matches"]:
            st.dataframe(
                pd.DataFrame(r["matches"])[
                    [
                        "level", "batch_match", "product", "batch", "manufacturer",
                        "alert_month", "list_type", "failure_reason", "citation",
                    ]
                ],
                hide_index=True,
                use_container_width=True,
            )

# ── How BatchWatch decides ───────────────────────────────────────────────────
with st.expander("How BatchWatch decides"):
    st.markdown("""
- **FLAGGED**: the batch number matches a published alert exactly **and** the product or manufacturer agrees.
- **POSSIBLE**: close but not certain (a likely OCR misread like 0/O, or the same code on a different product). A person must check the pack.
- **NOT IN ALERTS**: no published alert lists this batch. This is **not** a certificate of quality; only sampled batches are tested.

The AI reads labels and explains alerts. **It never decides the verdict**: that is deterministic code, and every flag cites the exact source file, serial number and page.
""")

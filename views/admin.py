import json

import pandas as pd
import streamlit as st

import ui
from core import ingest

ui.setup_page("Alert data")
a = ui.actor()
st.caption(
    "Step 1 of the agent loop, **Ingest**: new CDSCO alert files are parsed and validated, "
    "then wait for your approval before they are used."
)

# ── 1 · Inbox ────────────────────────────────────────────────────────────────
st.subheader("1 · New files in the inbox")
new = ingest.scan_inbox()
if not new:
    ui.empty_state(
        "📭",
        "Inbox is empty. New monthly alert PDFs go in `data/inbox/` "
        "(the scheduler watches this folder).",
    )
else:
    st.write(", ".join(f"`{p.name}`" for p in new))
    if st.button(f"Ingest and validate {len(new)} file(s)", type="primary"):
        with st.status("Parsing alert PDFs…", expanded=True) as status:
            for p in new:
                r = ingest.ingest_file(a, p)
                gap = "no gaps" if not r["missing"] else f"missing S.No {r['missing'][:8]}"
                st.write(
                    f"`{p.name}`: {r['rows']} rows, S.No 1–{r['max_sno']}, "
                    f"{gap}, validation **{r['validation']}**"
                )
            status.update(label="Parsed. Review and approve below.", state="complete")
        st.rerun()

# ── 2 · Pending approval ─────────────────────────────────────────────────────
st.subheader("2 · Waiting for approval")
pending = ingest.list_ingests("pending")
if not pending:
    ui.empty_state("✅", "Nothing waiting for approval.")
for p in pending:
    missing = json.loads(p["missing"] or "[]")
    c = st.container(border=True)
    c.markdown(
        f"**{p['source_file']}** · {p['alert_month']} · {p['list_type']} list · "
        f"{p['rows']} rows · validation **{p['validation']}**"
        + (f" (missing S.No {missing[:10]})" if missing else "")
    )
    b1, b2, _ = c.columns([1, 1, 4])
    if b1.button(
        "Approve → go live", key=f"ap{p['id']}", type="primary",
        disabled=p["validation"] != "passed",
    ):
        with st.spinner("Approving and re-checking every saved inventory and medicine cabinet…"):
            res = ingest.approve(a, p["id"])
        r = res["recheck"]
        st.session_state["last_recheck"] = (p["source_file"], r)
        st.rerun()
    if b2.button("Reject", key=f"rj{p['id']}"):
        ingest.reject(a, p["id"], "rejected by admin")
        st.rerun()

if "last_recheck" in st.session_state:
    f, r = st.session_state["last_recheck"]
    st.success(
        f"**{f}** is live. The agent re-checked {r['checked']} saved items: "
        f"{r['newly_flagged']} newly flagged, {r['inventory']} inventory and "
        f"{r['cabinet']} cabinet verdict change(s). Notifications sent to affected users."
    )

# ── 3 · Live data ────────────────────────────────────────────────────────────
st.subheader("3 · Live data used for matching")
live = pd.DataFrame(ingest.list_ingests("live"))
if live.empty:
    ui.empty_state("📋", "No live alert data yet. Approve a file above to activate it.")
else:
    st.dataframe(
        live[["source_file", "alert_month", "list_type", "rows",
              "validation", "reviewed_by", "reviewed_at"]],
        hide_index=True,
        use_container_width=True,
    )

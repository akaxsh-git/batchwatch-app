import uuid

import pandas as pd
import streamlit as st

import ui
from core import stock
from core.paths import DEMO_DIR

ui.setup_page("Stock check")
a = ui.actor()
agent = ui.get_agent()
st.caption(
    f"**{a['org']}** · Upload your inventory. The agent checks every line against live CDSCO "
    "alerts, plans quarantine and supplier returns, and waits for your approval before acting."
)

DEMO_FILES = {
    "Sunrise Pharmacy (Demo)": "inventory_sunrise_pharmacy_demo.csv",
    "CarePlus Hospital Pharmacy (Demo)": "inventory_careplus_hospital_demo.csv",
}
key = f"stock_thread::{a['org']}"

c1, c2 = st.columns([3, 2])
up = c1.file_uploader(
    "Inventory CSV (columns: product, batch, manufacturer, qty, supplier…)", type=["csv"]
)
use_demo = c2.button("Use demo inventory", use_container_width=True)
df = None
if up is not None:
    df = pd.read_csv(up)
elif use_demo and a["org"] in DEMO_FILES:
    df = pd.read_csv(DEMO_DIR / DEMO_FILES[a["org"]])

if df is not None:
    st.session_state[key] = str(uuid.uuid4())
    with st.spinner(f"Agent checking {len(df)} lines…"):
        st.session_state[key + "::run"] = agent.run(
            "stock", st.session_state[key],
            {"actor": a, "rows": df.to_dict("records"), "trace": []},
        )
    st.rerun()

run = st.session_state.get(key + "::run")
if run:
    state, wait = run["state"], run["waiting_for"]
    c = state["check"]["counts"]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Lines checked", state["check"]["lines"])
    m2.metric("FLAGGED", c["FLAGGED"])
    m3.metric("POSSIBLE (check pack)", c["POSSIBLE"])
    m4.metric("Check time", f"{state['check']['seconds']} s")
    ui.show_trace(state["trace"], expanded=True)

    if wait and wait["type"] == "approve_stock_actions":
        st.subheader("Your approval is needed")
        inv = stock.get_inventory(a)
        flagged = inv[inv.verdict.isin(["FLAGGED", "POSSIBLE"])]
        st.dataframe(
            flagged[["id", "verdict", "product", "batch", "qty",
                      "supplier", "failure_reason", "citation"]],
            hide_index=True,
            use_container_width=True,
        )
        opts = flagged.id.tolist()
        default = list(wait["plan"]["flagged_ids"])
        q_ids = st.multiselect(
            "Quarantine these lines (take off sale)", opts, default=default,
            format_func=lambda i: (
                f"#{i} {flagged.set_index('id').loc[i, 'product']} · "
                f"{flagged.set_index('id').loc[i, 'batch']} · "
                f"{flagged.set_index('id').loc[i, 'verdict']}"
            ),
        )
        if wait["plan"]["possible_ids"]:
            st.info("POSSIBLE lines are not pre-selected: check the batch printed on the pack first.")
        approve_ids = []
        for d in wait["drafts"]:
            with st.expander(
                f"Draft return request → {d['supplier']} ({d['n_items']} batch(es)) · {d['source']}"
            ):
                st.text(f"Subject: {d['subject']}\n\n{d['body']}")
                if st.checkbox("Approve and send this request", key=f"d{d['action_id']}", value=True):
                    approve_ids.append(d["action_id"])
        if st.button("Apply my decisions", type="primary"):
            reject_ids = [d["action_id"] for d in wait["drafts"] if d["action_id"] not in approve_ids]
            with st.spinner("Applying and writing the compliance report…"):
                st.session_state[key + "::run"] = agent.run(
                    "stock", st.session_state[key],
                    resume={
                        "quarantine_ids": q_ids,
                        "approve_action_ids": approve_ids,
                        "reject_action_ids": reject_ids,
                    },
                )
            st.rerun()

    if run["done"]:
        st.success("Done. Decisions applied and logged.")
        rep = state.get("report", {}).get("markdown", "")
        with st.expander("Compliance report", expanded=False):
            st.markdown(rep)
        d1, d2 = st.columns(2)
        d1.download_button(
            "Download compliance report (.md)", rep,
            file_name="batchwatch_compliance_report.md",
        )
        inv = stock.get_inventory(a)
        d2.download_button(
            "Download checked inventory (.csv)", inv.to_csv(index=False),
            file_name="batchwatch_inventory_checked.csv",
        )

# ── Current inventory status ─────────────────────────────────────────────────
st.subheader("Current inventory status")
inv = stock.get_inventory(a)
if inv.empty:
    ui.empty_state("🏥", "No inventory checked yet. Upload a CSV or use the demo inventory above.")
else:
    show = st.radio("Show", ["Flagged & possible", "All"], horizontal=True)
    view = inv if show == "All" else inv[inv.verdict.isin(["FLAGGED", "POSSIBLE"])]
    st.dataframe(
        view[["verdict", "status", "product", "batch", "manufacturer", "qty",
              "supplier", "alert_month", "failure_reason", "citation"]],
        hide_index=True,
        use_container_width=True,
    )

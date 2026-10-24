import pandas as pd
import streamlit as st

import ui
from core import audit, db, ingest, report

ui.setup_page("Audit trail & reports")
a = ui.actor()
scope = {
    "admin": "all users and the agent",
    "pharmacist": f"everyone at {a.get('org')}",
    "household": "your own activity",
}[a["role"]]
st.caption(
    f"Every tool call, AI reading, human decision and denied attempt is recorded. "
    f"You can see: **{scope}**."
)

rows = pd.DataFrame(audit.fetch(a))
if rows.empty:
    ui.empty_state("🧾", "No activity yet. Actions appear here as you use the app.")
else:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Entries", len(rows))
    m2.metric("Human decisions", int(rows.action.str.startswith("human:").sum()))
    m3.metric("Agent tool calls", int(rows.action.str.startswith("tool:").sum()))
    m4.metric("Denied attempts", int((rows.status == "denied").sum()))
    f1, f2 = st.columns(2)
    kinds = f1.multiselect("Action", sorted(rows.action.unique()))
    who = f2.multiselect("Actor", sorted(rows.actor.dropna().unique()))
    view = rows
    if kinds:
        view = view[view.action.isin(kinds)]
    if who:
        view = view[view.actor.isin(who)]
    st.dataframe(
        view[["ts", "actor", "role", "org", "action", "verdict", "citation", "status", "input", "output"]],
        hide_index=True,
        use_container_width=True,
        height=420,
    )
    st.download_button(
        "Export audit log (.csv)", view.to_csv(index=False),
        file_name="batchwatch_audit_log.csv",
    )

if a["role"] in ("admin", "pharmacist"):
    st.subheader("Compliance report")
    org = a.get("org")
    if a["role"] == "admin":
        orgs = [u["org"] for u in db.list_users() if u["role"] == "pharmacist"]
        org = st.selectbox("Organisation", orgs)
    if st.button("Generate report", type="primary"):
        r = report.compliance_report(a, org)
        st.markdown(r["markdown"])
        st.download_button(
            "Download (.md)", r["markdown"], file_name=f"compliance_{org}.md"
        )

if a["role"] != "admin":
    st.subheader("Access control check")
    st.caption(
        "Permissions are enforced in the backend, not just by hiding pages. "
        "Try an admin-only action:"
    )
    if st.button("Try to approve alert data as this user"):
        try:
            ingest.approve(a, 1)
            st.error("Unexpected: the action was allowed")
        except PermissionError as e:
            st.success(
                f"Blocked as expected: {e}. The attempt is now in the audit log as 'denied'."
            )

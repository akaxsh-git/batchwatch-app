"""Manual batch search page — available to household and pharmacist roles.

Two tabs:
  • Search by batch number — uses the existing matcher, shows the same verdict card.
  • Browse alerts by product name — raw DB rows clearly labelled as "browse, not a verdict".

Audit-logged. No personal data in the log.
"""
import html

import streamlit as st

import ui
from core import auth, audit, matcher
from core.db import session

a = ui.actor()
auth.require(a, "batch_search")

ui.setup_page("🔍 Batch Search")
st.caption(
    "Search our live CDSCO alert database directly — no photo needed. "
    "The same matching engine used by the scan tool."
)

tab_search, tab_browse = st.tabs(["🔎 Search by batch number", "📋 Browse alerts by product"])

# ── Tab 1: Search by batch number ────────────────────────────────────────────
with tab_search:
    st.markdown("#### Search by Batch Number")
    st.caption(
        "Enter the batch number printed on the medicine pack. "
        "Optionally add the product name to improve accuracy."
    )

    with st.form("search_form"):
        col1, col2 = st.columns([2, 3])
        batch_input = col1.text_input(
            "Batch number *",
            placeholder="e.g. BN2024001",
            help="Required. Found on the strip, bottle or box.",
        )
        product_input = col2.text_input(
            "Product / medicine name (optional)",
            placeholder="e.g. Amoxicillin",
            help="Helps confirm the match. Leave blank if unsure.",
        )
        submitted = st.form_submit_button("Search", type="primary", use_container_width=True)

    if submitted:
        batch_clean = batch_input.strip()
        product_clean = product_input.strip() or None

        if not batch_clean:
            st.warning("Please enter a batch number to search.")
        else:
            with st.spinner("Checking live alert database…"):
                result = matcher.match(batch_clean, product=product_clean)

            # Audit — log the action without personal data
            audit.log(
                a,
                "batch_search",
                input={"batch": batch_clean, "product": product_clean},
                output={"verdict": result["verdict"], "citation": result.get("citation")},
                verdict=result["verdict"],
                citation=result.get("citation"),
            )

            # Show verdict
            ui.verdict_card(result)

            # Extra detail for POSSIBLE: show all nearby matches
            if result["verdict"] == "POSSIBLE" and len(result.get("matches", [])) > 1:
                with st.expander(f"All {len(result['matches'])} nearby match(es)"):
                    for m in result["matches"]:
                        st.markdown(
                            f"- **{m['batch']}** — {html.escape(m.get('product', ''))}  "
                            f"  <span class='cite'>{html.escape(m.get('citation', ''))}</span>",
                            unsafe_allow_html=True,
                        )

            if result["verdict"] == "CLEAR":
                st.caption(
                    "ℹ️ **Note:** 'Not in published alerts' means this batch was not found in any "
                    "admin-approved CDSCO alert in our database. It does not mean the medicine is "
                    "certified or tested. Always check the expiry date and buy from licensed sources."
                )

# ── Tab 2: Browse alerts by product name ─────────────────────────────────────
with tab_browse:
    st.markdown("#### Browse Alerts by Product Name")
    st.info(
        "🗂️ **Browse mode** — this lists matching rows from the CDSCO alert database. "
        "It is **not a verdict** on any specific batch you hold. "
        "Use the 'Search by batch number' tab for a verdict on your medicine.",
        icon="ℹ️",
    )

    browse_query = st.text_input(
        "Product / medicine name",
        placeholder="e.g. Paracetamol",
        key="browse_q",
    )

    if browse_query.strip():
        q = f"%{browse_query.strip()}%"
        with session() as con:
            rows = [
                dict(r)
                for r in con.execute(
                    """
                    SELECT a.product, a.batch, a.batch_norm, a.manufacturer,
                           a.alert_month, a.list_type, a.source_file, a.sno, a.page,
                           a.mfg_date, a.exp_date, a.nsq_result
                    FROM alerts a
                    JOIN ingests i ON i.id = a.ingest_id
                    WHERE i.status = 'live'
                      AND (a.product LIKE ? COLLATE NOCASE
                           OR a.manufacturer LIKE ? COLLATE NOCASE)
                    ORDER BY a.alert_month DESC, a.sno
                    LIMIT 100
                    """,
                    (q, q),
                )
            ]

        if not rows:
            ui.empty_state("🔍", f"No live alerts found matching '{browse_query.strip()}'.")
        else:
            st.caption(
                f"Found **{len(rows)}** alert row(s) matching your query "
                f"(capped at 100). These are raw CDSCO records — not a verdict on your batch."
            )
            # Render as a clean table
            import pandas as pd

            df = pd.DataFrame(rows)[
                ["product", "batch", "manufacturer", "alert_month", "list_type",
                 "mfg_date", "exp_date", "nsq_result", "source_file", "sno"]
            ]
            df.columns = [
                "Product", "Batch", "Manufacturer", "Alert Month", "List",
                "Mfg Date", "Exp Date", "Lab Finding", "Source File", "S.No"
            ]
            st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        ui.empty_state("📋", "Type a product or medicine name above to browse alert records.")

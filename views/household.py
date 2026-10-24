import uuid
from pathlib import Path

import streamlit as st

import ui
from core import cabinet
from core.paths import DEMO_DIR

ui.setup_page("Scan a medicine")
a = ui.actor()
agent = ui.get_agent()
st.caption(
    "Photograph the side of the strip or carton that shows the batch number (B.No.). "
    "Only the photo is sent to the AI, never your name, and it is discarded after reading."
)

S = st.session_state
S.setdefault("h_attempt", 1)


def start(img_bytes, filename):
    S["h_thread"] = str(uuid.uuid4())
    S["h_image"] = img_bytes
    S["h_run"] = agent.run(
        "household", S["h_thread"],
        {"actor": a, "image": img_bytes, "filename": filename,
         "attempt": S["h_attempt"], "trace": []},
    )


def resume(payload):
    S["h_run"] = agent.run("household", S["h_thread"], resume=payload)


tab1, tab2, tab3 = st.tabs(["📷 Camera", "⬆️ Upload photo", "🧪 Demo labels"])
with tab1:
    cam = st.camera_input("Take a photo")
    if cam and st.button("Check this photo", key="cam_go", type="primary"):
        start(cam.getvalue(), "camera.jpg"); st.rerun()
with tab2:
    up = st.file_uploader("Photo of the strip", type=["jpg", "jpeg", "png"])
    if up and st.button("Check this photo", key="up_go", type="primary"):
        start(up.getvalue(), up.name); st.rerun()
with tab3:
    demo = sorted((Path(DEMO_DIR) / "labels").glob("*.jpg"))
    if not demo:
        ui.empty_state("🖼️", "No demo label images found in data/demo/labels/.")
    else:
        cols = st.columns(len(demo))
        for col, p in zip(cols, demo):
            col.image(str(p), caption=p.stem.split("_", 1)[1].replace("_", " "), use_container_width=True)
            if col.button("Scan", key=f"demo_{p.name}"):
                start(p.read_bytes(), p.name); st.rerun()

run = S.get("h_run")
if run:
    st.divider()
    state, wait = run["state"], run["waiting_for"]
    left, right = st.columns([1, 2])
    if S.get("h_image"):
        left.image(S["h_image"], caption="Photo (not stored)", use_container_width=True)
    with right:
        if wait and wait["type"] == "confirm_batch":
            f, c = wait["fields"], wait["confidence"]
            st.subheader("Step 1 · Confirm what the AI read")
            (st.warning if wait["low_confidence"] else st.info)(wait["message"])
            with st.form("confirm"):
                batch = st.text_input(
                    f"Batch number (AI confidence {c.get('batch_number', 0):.0%})",
                    value=f.get("batch_number") or "",
                )
                product = st.text_input(
                    "Medicine", value=f.get("generic_name") or f.get("brand_name") or ""
                )
                maker = st.text_input("Manufacturer", value=f.get("manufacturer") or "")
                expiry = st.text_input("Expiry", value=f.get("expiry_date") or "")
                b1, b2 = st.columns(2)
                ok = b1.form_submit_button("Confirm and check", type="primary")
                retake = b2.form_submit_button("Retake photo")
            if ok and batch.strip():
                resume({"action": "confirm", "batch": batch, "product": product,
                        "manufacturer": maker, "expiry": expiry})
                st.rerun()
            if retake:
                resume({"action": "retake"}); S["h_attempt"] += 1; st.rerun()

        elif wait and wait["type"] == "recheck_strip":
            st.subheader("Step 2 · Please look at the pack again")
            st.warning(wait["message"])
            st.write(f"You confirmed **{wait['your_batch']}**. Closest listed batch(es):")
            for cnd in wait["candidates"]:
                st.markdown(
                    f"- **{cnd['batch']}** · {cnd['product']} · "
                    f"<span class='cite'>{cnd['citation']}</span>",
                    unsafe_allow_html=True,
                )
            nb = st.text_input(
                "If the pack shows a different batch, type it exactly",
                value=wait["your_batch"],
            )
            b1, b2 = st.columns(2)
            if b1.button("Check corrected batch", type="primary"):
                resume({"action": "edit_batch", "batch": nb}); st.rerun()
            if b2.button("The batch is exactly as I typed"):
                resume({"action": "keep"}); st.rerun()

        elif wait and wait["type"] == "approve_report":
            ui.verdict_card(state["result"], state.get("explanation"))
            st.subheader("Report it? (optional)")
            st.caption(
                "The agent drafted a report to the State Drug Controller. Nothing is sent unless "
                "you approve. Your name and contact details are not included."
            )
            body = st.text_area("Draft report", wait["draft"]["body"], height=220)
            b1, b2 = st.columns(2)
            if b1.button("Approve and send", type="primary"):
                resume({"approve": True, "body": body}); st.rerun()
            if b2.button("Don't send"):
                resume({"approve": False}); st.rerun()

        elif state.get("status") == "retake":
            st.warning(
                "I couldn't read the batch number clearly. Please take a sharper photo of the "
                "batch area, in good light, without glare."
                + (" Next time you can also type the batch number yourself."
                   if S["h_attempt"] >= 2 else "")
            )
            if S["h_attempt"] < 2 and st.button("OK, I'll retake"):
                S["h_attempt"] += 1; S.pop("h_run"); st.rerun()

        elif run["done"] and state.get("result"):
            ui.verdict_card(state["result"], state.get("explanation"))
            if state.get("report", {}).get("status") == "approved":
                st.success("Your report was sent to the State Drug Controller.")
            st.caption(
                "Saved to your medicine cabinet. "
                "We'll re-check it automatically when new alerts are published."
            )
            if st.button("Scan another medicine"):
                for k in ("h_run", "h_image", "h_thread"):
                    S.pop(k, None)
                S["h_attempt"] = 1; st.rerun()
        ui.show_trace(state.get("trace", []))

# ── Medicine cabinet ──────────────────────────────────────────────────────────
st.divider()
st.subheader("My medicine cabinet")
items = cabinet.list_items(a)
if not items:
    ui.empty_state(
        "💊",
        "Nothing saved yet. Scan a medicine above to add it to your cabinet.",
    )
for it in items:
    c1, c2 = st.columns([6, 1])
    c1.markdown(
        f"{ui.pill(it['verdict'])} **{it['product'] or 'Medicine'}** · "
        f"batch `{it['batch']}` · exp {it['expiry'] or '–'}"
        + (f" · <span class='cite'>{it['citation']}</span>" if it["citation"] else "")
        + f"  \n<span class='muted'>last checked {it['checked_at']}</span>",
        unsafe_allow_html=True,
    )
    if c2.button("Remove", key=f"rm{it['id']}"):
        cabinet.remove(a, it["id"]); st.rerun()

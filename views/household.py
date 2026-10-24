import uuid
from pathlib import Path

import streamlit as st

import ui
from agent import imgcheck, translate
from core import cabinet
from core.paths import DEMO_DIR

a = ui.actor()
agent = ui.get_agent()
lang = ui.current_lang()

ui.setup_page(translate.get_ui_string("scan_title", lang))
st.caption(translate.get_ui_string("scan_caption", lang))

S = st.session_state
S.setdefault("h_attempt", 1)

# ── Confusable character highlight map (for Feature 3) ────────────────────────
_CONFUSABLE = {
    "0": ("O", "Q", "D"),
    "1": ("I", "L"),
    "2": ("Z",),
    "5": ("S",),
    "6": ("G",),
    "8": ("B",),
}
# Build a reverse map: char → note
_CHAR_HINTS: dict[str, str] = {}
for digit, lookalikes in _CONFUSABLE.items():
    for lk in lookalikes:
        _CHAR_HINTS[lk] = f"Can look like '{digit}'"
        _CHAR_HINTS[lk.lower()] = f"Can look like '{digit}'"
    _CHAR_HINTS[digit] = f"Could be mistaken for: {', '.join(lookalikes)}"


def _highlight_batch(batch_str: str) -> str:
    """Return HTML with confusable chars wrapped in a coloured span + tooltip."""
    out = []
    for ch in batch_str:
        if ch.upper() in {k.upper() for k in _CHAR_HINTS}:
            hint = _CHAR_HINTS.get(ch) or _CHAR_HINTS.get(ch.upper(), "")
            out.append(
                f'<span style="background:rgba(245,158,11,0.25);border-radius:3px;'
                f'padding:0 2px;border-bottom:2px solid #F59E0B;" '
                f'title="{hint}">{ch}</span>'
            )
        else:
            out.append(ch)
    return "".join(out)


def _confidence_bar(conf_value: float, label: str = ""):
    """Show a colour-coded confidence progress bar."""
    pct = int(conf_value * 100)
    if pct >= 80:
        color = "#15803D"
        text = "High confidence"
    elif pct >= 50:
        color = "#D97706"
        text = "Medium confidence"
    else:
        color = "#DC2626"
        text = "Low confidence — please verify carefully"
    bar_html = (
        f'<div style="margin:8px 0;">'
        f'<div style="font-size:0.8rem;opacity:0.7;margin-bottom:4px;">'
        f'AI confidence for {label or "this field"}: <b>{pct}%</b> — {text}</div>'
        f'<div style="background:rgba(148,163,184,0.15);border-radius:6px;height:8px;">'
        f'<div style="width:{pct}%;background:{color};border-radius:6px;height:8px;"></div>'
        f'</div></div>'
    )
    st.markdown(bar_html, unsafe_allow_html=True)


def _quality_gate(img_bytes: bytes, source_key: str) -> bool:
    """Show quality warnings; return True if we should proceed to Gemini.

    Returns True if image is OK or user clicked "Use anyway".
    Returns False if user should retake.
    """
    qr = imgcheck.check_image_quality(img_bytes)
    if qr["ok"]:
        return True

    # Image has issues — show advice and let user decide
    st.warning("**Image quality check**")
    for advice in qr["advice"]:
        st.markdown(f"- {advice}")
    w, h = qr["resolution"]
    st.caption(
        f"Blur score: {qr['blur']:.0f} (min {imgcheck.THRESHOLDS['blur_min']}) · "
        f"Brightness: {qr['brightness']:.0f} · "
        f"Resolution: {w}×{h}px"
    )
    col1, col2 = st.columns(2)
    if col1.button("🔄 Retake photo", key=f"retake_quality_{source_key}", type="primary"):
        return False
    if col2.button("⚠️ Use anyway", key=f"use_anyway_{source_key}"):
        return True
    # No button pressed yet → block until user decides
    st.stop()


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


tab1, tab2, tab3 = st.tabs([
    translate.get_ui_string("tab_camera", lang),
    translate.get_ui_string("tab_upload", lang),
    translate.get_ui_string("tab_demo", lang),
])

with tab1:
    cam = st.camera_input("Take a photo")
    if cam and st.button("Check this photo", key="cam_go", type="primary"):
        if _quality_gate(cam.getvalue(), "cam"):
            start(cam.getvalue(), "camera.jpg")
            st.rerun()

with tab2:
    up = st.file_uploader("Photo of the strip", type=["jpg", "jpeg", "png"])
    if up and st.button("Check this photo", key="up_go", type="primary"):
        if _quality_gate(up.getvalue(), "up"):
            start(up.getvalue(), up.name)
            st.rerun()

with tab3:
    demo = sorted((Path(DEMO_DIR) / "labels").glob("*.jpg"))
    if not demo:
        ui.empty_state("🖼️", "No demo label images found in data/demo/labels/.")
    else:
        cols = st.columns(len(demo))
        for col, p in zip(cols, demo):
            col.image(str(p), caption=p.stem.split("_", 1)[1].replace("_", " "), use_container_width=True)
            if col.button("Scan", key=f"demo_{p.name}"):
                # Demo images skip quality gate — they are pre-checked reference photos
                start(p.read_bytes(), p.name)
                st.rerun()

run = S.get("h_run")
if run:
    st.divider()
    state, wait = run["state"], run["waiting_for"]

    if wait and wait["type"] == "confirm_batch":
        # ── Feature 3: Better batch confirmation ─────────────────────────────
        f, c = wait["fields"], wait["confidence"]
        batch_ai = f.get("batch_number") or ""
        conf_batch = c.get("batch_number", 0.0)

        # Two-column layout: photo on left, form on right
        left, right = st.columns([1, 2])

        if S.get("h_image"):
            with left:
                st.markdown("**📸 Your photo**")
                st.image(S["h_image"], use_container_width=True, caption="Tap to zoom")
                st.caption("*Photo is not stored.*")

        with right:
            st.subheader(translate.get_ui_string("step_confirm_title", lang))
            (st.warning if wait["low_confidence"] else st.info)(wait["message"])

            # Confusable-char highlight for the AI-read batch
            if batch_ai:
                st.markdown(
                    f"<div style='margin:6px 0 2px;font-size:0.82rem;opacity:0.7;'>"
                    f"AI read the batch number as — "
                    f"highlighted characters may be misread:</div>"
                    f"<div style='font-family:monospace;font-size:1.3rem;letter-spacing:3px;"
                    f"padding:8px 12px;border-radius:8px;"
                    f"background:rgba(148,163,184,0.1);margin-bottom:4px;'>"
                    f"{_highlight_batch(batch_ai)}</div>",
                    unsafe_allow_html=True,
                )
                st.caption(
                    "🔸 Orange-highlighted characters look similar to other characters. "
                    "Hover over them (or compare with your pack) to see what they might be confused with."
                )
                _confidence_bar(conf_batch, "batch number")

            with st.form("confirm"):
                batch = st.text_input(
                    "Batch number — edit if needed",
                    value=batch_ai,
                    help="Compare carefully with the physical pack. "
                         "Watch for 0/O, 1/I/L, 5/S, 8/B, 2/Z.",
                )
                product = st.text_input(
                    "Medicine", value=f.get("generic_name") or f.get("brand_name") or ""
                )
                maker = st.text_input("Manufacturer", value=f.get("manufacturer") or "")
                expiry = st.text_input("Expiry", value=f.get("expiry_date") or "")
                b1, b2 = st.columns(2)
                ok = b1.form_submit_button(translate.get_ui_string("btn_confirm", lang), type="primary")
                retake = b2.form_submit_button(translate.get_ui_string("btn_retake", lang))
            if ok and batch.strip():
                resume({"action": "confirm", "batch": batch, "product": product,
                        "manufacturer": maker, "expiry": expiry})
                st.rerun()
            if retake:
                resume({"action": "retake"}); S["h_attempt"] += 1; st.rerun()

    else:
        left, right = st.columns([1, 2])
        if S.get("h_image"):
            left.image(S["h_image"], caption="Photo (not stored)", use_container_width=True)
        with right:
            if wait and wait["type"] == "recheck_strip":
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
                if st.button(translate.get_ui_string("scan_another", lang)):
                    for k in ("h_run", "h_image", "h_thread"):
                        S.pop(k, None)
                    S["h_attempt"] = 1; st.rerun()
            ui.show_trace(state.get("trace", []))

# ── Medicine cabinet ──────────────────────────────────────────────────────────
st.divider()
st.subheader(translate.get_ui_string("cabinet_title", lang))
items = cabinet.list_items(a)
if not items:
    ui.empty_state(
        "💊",
        translate.get_ui_string("cabinet_empty", lang),
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

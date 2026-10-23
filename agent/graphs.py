"""BatchWatch agent workflows as LangGraph graphs.

Each node is a step; edges decide what happens next based on results.
`interrupt()` pauses the graph for a human decision (the human gates);
the UI resumes it with Command(resume=...). Every step appends to `trace`,
which the UI shows as the agent's reasoning, and tools write to the audit log.

Household graph:
  read_label -> [no batch?] -> retake / manual entry
             -> confirm_batch (PAUSE: human confirms or corrects)
             -> match -> FLAGGED  -> explain -> draft_report -> approve_report (PAUSE) -> save
                      -> POSSIBLE -> recheck_strip (PAUSE: edit batch or keep) -> match / save
                      -> CLEAR    -> save

Stock graph:
  check -> plan -> draft_returns -> approve (PAUSE: quarantine + approve drafts) -> apply -> report
"""
import operator
from typing import Annotated, Any, Optional, TypedDict

import pandas as pd
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from core import actions, cabinet, report, stock
from core.audit import log
from . import tools

CONFIDENCE_OK = 0.85
MAX_ATTEMPTS = 2


# ======================================================== household graph
class HouseState(TypedDict, total=False):
    actor: dict
    image: bytes
    filename: str
    attempt: int
    read: dict
    item: dict            # confirmed product/batch/manufacturer/expiry
    result: dict          # matcher output
    explanation: dict
    report: dict
    saved: dict
    status: str
    trace: Annotated[list, operator.add]


def h_read(s: HouseState):
    r = tools.read_label(s["actor"], s["image"], s.get("filename", ""))
    b, c = r["fields"].get("batch_number"), r["confidence"].get("batch_number", 0)
    msg = f"Read label with {r['source']}: batch {b or '—'} (confidence {c:.2f})"
    if r.get("note"):
        msg += f". {r['note']}"
    return {"read": r, "image": b"", "trace": [msg]}  # drop the photo from state once read


def h_after_read(s: HouseState):
    batch = s["read"]["fields"].get("batch_number")
    if batch:
        return "confirm"
    return "confirm" if s.get("attempt", 1) >= MAX_ATTEMPTS else "retake"


def h_retake(s: HouseState):
    return {"status": "retake", "trace": [f"Batch number unreadable → asking for a clearer photo "
                                          f"(attempt {s.get('attempt', 1)} of {MAX_ATTEMPTS})"]}


def h_confirm(s: HouseState):
    f, c = s["read"]["fields"], s["read"]["confidence"]
    low = (c.get("batch_number") or 0) < CONFIDENCE_OK
    answer = interrupt({
        "type": "confirm_batch", "fields": f, "confidence": c, "low_confidence": low,
        "manual": not f.get("batch_number"),
        "message": ("I'm not fully sure about the batch number. Please compare it with the pack and correct it."
                    if low else "Please check the batch number matches the pack."),
    })
    if answer.get("action") == "retake":
        return {"status": "retake", "trace": ["User asked to retake the photo"]}
    item = {"product": answer.get("product") or f.get("generic_name") or f.get("brand_name"),
            "batch": answer["batch"].strip(), "manufacturer": answer.get("manufacturer") or f.get("manufacturer"),
            "expiry": answer.get("expiry") or f.get("expiry_date")}
    changed = (item["batch"] or "").replace(" ", "").upper() != (f.get("batch_number") or "").replace(" ", "").upper()
    log(s["actor"], "human:confirm_batch", {"read": f.get("batch_number")}, {"confirmed": item["batch"], "corrected": changed})
    return {"item": item, "trace": [f"User confirmed batch {item['batch']}" + (" (corrected from the AI's reading)" if changed else "")]}


def h_after_confirm(s: HouseState):
    return END if s.get("status") == "retake" else "match"


def h_match(s: HouseState):
    it = s["item"]
    res = tools.match_batch(s["actor"], it["batch"], it.get("product"), it.get("manufacturer"))
    extra = f" (flagged in {res['times_flagged']} separate alerts)" if res.get("times_flagged", 0) > 1 else ""
    return {"result": res, "trace": [f"Matcher verdict: {res['verdict']}" + (f" · {res['citation']}" if res["citation"] else "") + extra]}


def h_route(s: HouseState):
    return {"FLAGGED": "explain", "POSSIBLE": "recheck_strip"}.get(s["result"]["verdict"], "save")


def h_explain(s: HouseState):
    top = s["result"]["matches"][0]
    e = tools.explain_alert(s["actor"], top)
    return {"explanation": e, "trace": [f"Explained the alert in plain language ({e['source']}), using only the cited row"]}


def h_draft_report(s: HouseState):
    top = s["result"]["matches"][0]
    d = tools.draft_controller_report(s["actor"], s["item"], top)
    return {"report": {"action_id": d["action_id"], "subject": d["subject"], "body": d["body"], "status": "draft"},
            "trace": ["Drafted a report to the State Drug Controller. Waiting for the user's approval"]}


def h_approve_report(s: HouseState):
    # interrupt first: on resume this node re-runs from the top, so no side effects before it
    d = s["report"]
    answer = interrupt({"type": "approve_report", "draft": {"id": d["action_id"], "subject": d["subject"], "body": d["body"]}})
    decision = actions.decide(s["actor"], d["action_id"], bool(answer.get("approve")), answer.get("body"))
    return {"report": {**d, **decision},
            "trace": [f"Report {'approved and sent' if decision['status'] == 'approved' else 'not sent'} by the user"]}


def h_recheck_strip(s: HouseState):
    cands = [{"batch": m["batch"], "product": m["product"], "why": m["batch_match"], "citation": m["citation"]}
             for m in s["result"]["matches"][:3]]
    answer = interrupt({"type": "recheck_strip", "candidates": cands, "your_batch": s["item"]["batch"],
                        "message": "This is close to a listed batch but not certain. Please look at the pack again."})
    if answer.get("action") == "edit_batch":
        log(s["actor"], "human:edit_batch", {"from": s["item"]["batch"]}, {"to": answer["batch"]})
        return {"item": {**s["item"], "batch": answer["batch"].strip()},
                "trace": [f"User re-checked the pack and corrected the batch to {answer['batch']}"]}
    return {"status": "keep_possible", "trace": ["User confirmed the batch as read; kept as POSSIBLE for a pharmacist to check"]}


def h_after_recheck(s: HouseState):
    return "save" if s.get("status") == "keep_possible" else "match"


def h_save(s: HouseState):
    it, res = s["item"], s["result"]
    saved = cabinet.add(s["actor"], it.get("product"), it["batch"], it.get("manufacturer"), it.get("expiry"),
                        res["verdict"], res.get("citation"), res.get("alert_id"))
    return {"saved": saved, "status": "done",
            "trace": ["Saved to your medicine cabinet. It will be re-checked automatically when new alerts are published"]}


def build_household(checkpointer):
    g = StateGraph(HouseState)
    for name, fn in [("read_label", h_read), ("retake", h_retake), ("confirm_batch", h_confirm), ("match", h_match),
                     ("explain", h_explain), ("draft_report", h_draft_report), ("approve_report", h_approve_report), ("recheck_strip", h_recheck_strip),
                     ("save", h_save)]:
        g.add_node(name, fn)
    g.add_edge(START, "read_label")
    g.add_conditional_edges("read_label", h_after_read, {"confirm": "confirm_batch", "retake": "retake"})
    g.add_edge("retake", END)
    g.add_conditional_edges("confirm_batch", h_after_confirm, {"match": "match", END: END})
    g.add_conditional_edges("match", h_route, {"explain": "explain", "recheck_strip": "recheck_strip", "save": "save"})
    g.add_edge("explain", "draft_report")
    g.add_edge("draft_report", "approve_report")
    g.add_edge("approve_report", "save")
    g.add_conditional_edges("recheck_strip", h_after_recheck, {"save": "save", "match": "match"})
    g.add_edge("save", END)
    return g.compile(checkpointer=checkpointer)


# ======================================================== stock graph
class StockState(TypedDict, total=False):
    actor: dict
    rows: list            # uploaded inventory as list of dicts
    check: dict
    plan: dict
    drafts: list
    applied: dict
    report: dict
    trace: Annotated[list, operator.add]


def s_check(s: StockState):
    r = stock.check_inventory(s["actor"], pd.DataFrame(s["rows"]))
    c = r["counts"]
    return {"check": r, "rows": [], "trace": [f"Checked {r['lines']} inventory lines against live CDSCO alerts in "
                                              f"{r['seconds']} s: {c['FLAGGED']} FLAGGED, {c['POSSIBLE']} POSSIBLE, "
                                              f"{c['CLEAR']} not in published alerts"]}


def s_plan(s: StockState):
    inv = stock.get_inventory(s["actor"])
    fl, po = inv[inv.verdict == "FLAGGED"], inv[inv.verdict == "POSSIBLE"]
    plan = {"flagged_ids": fl.id.tolist(), "possible_ids": po.id.tolist(),
            "suppliers": sorted(fl.supplier.unique().tolist())}
    steps = [f"Plan: quarantine {len(fl)} flagged line(s); draft return requests to {len(plan['suppliers'])} supplier(s)"]
    if len(po):
        steps.append(f"{len(po)} POSSIBLE line(s) need a pharmacist to check the pack before any action")
    return {"plan": plan, "trace": steps}


def s_draft(s: StockState):
    if not s["plan"]["flagged_ids"]:
        return {"drafts": [], "trace": ["Nothing flagged; no drafts needed"]}
    drafts = tools.draft_supplier_returns(s["actor"])
    return {"drafts": [{"action_id": d["action_id"], "supplier": d["supplier"], "subject": d["subject"],
                        "body": d["body"], "source": d["source"], "n_items": len(d["items"])} for d in drafts],
            "trace": [f"Drafted {len(drafts)} supplier return request(s) ({drafts[0]['source'] if drafts else '-'}). Waiting for approval"]}


def s_approve(s: StockState):
    answer = interrupt({"type": "approve_stock_actions", "plan": s["plan"], "drafts": s.get("drafts", [])})
    return {"applied": answer}


def s_apply(s: StockState):
    a = s["applied"] or {}
    q = stock.quarantine(s["actor"], a.get("quarantine_ids", [])) if a.get("quarantine_ids") else {"quarantined": 0}
    approved = [actions.decide(s["actor"], i, True) for i in a.get("approve_action_ids", [])]
    rejected = [actions.decide(s["actor"], i, False) for i in a.get("reject_action_ids", [])]
    return {"trace": [f"Pharmacist approved: {q['quarantined']} line(s) quarantined, {len(approved)} return request(s) sent, "
                      f"{len(rejected)} rejected"]}


def s_report(s: StockState):
    r = report.compliance_report(s["actor"])
    return {"report": {"markdown": r["markdown"], "counts": r["counts"]},
            "trace": ["Compliance report generated with every decision and its source citation"]}


def build_stock(checkpointer):
    g = StateGraph(StockState)
    for name, fn in [("check", s_check), ("plan", s_plan), ("draft_returns", s_draft), ("approve", s_approve),
                     ("apply", s_apply), ("report", s_report)]:
        g.add_node(name, fn)
    g.add_edge(START, "check")
    g.add_edge("check", "plan")
    g.add_edge("plan", "draft_returns")
    g.add_edge("draft_returns", "approve")
    g.add_edge("approve", "apply")
    g.add_edge("apply", "report")
    g.add_edge("report", END)
    return g.compile(checkpointer=checkpointer)


# ======================================================== runner helpers
class Agent:
    """Holds compiled graphs and one checkpointer (in memory for the demo)."""

    def __init__(self):
        self.saver = InMemorySaver()
        self.household = build_household(self.saver)
        self.stock = build_stock(self.saver)

    @staticmethod
    def _cfg(thread_id):
        return {"configurable": {"thread_id": thread_id}}

    def run(self, graph, thread_id, state=None, resume=None) -> dict:
        g = getattr(self, graph)
        out = g.invoke(Command(resume=resume) if resume is not None else state, self._cfg(thread_id))
        snap = g.get_state(self._cfg(thread_id))
        pending = [i.value for t in snap.tasks for i in t.interrupts]
        return {"state": snap.values, "waiting_for": pending[0] if pending else None, "done": not snap.next}

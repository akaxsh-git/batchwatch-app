"""Append-only audit trail.

Every agent tool and every user decision goes through log(). The @audited
decorator wraps a function so its call, result and verdict are recorded
automatically, so logging can't be forgotten.
Images and full documents are never stored here, only short summaries.
"""
import functools
import json
from datetime import datetime, timezone

from .db import session


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _short(obj, limit=600):
    if obj is None:
        return None
    try:
        s = json.dumps(obj, default=str, ensure_ascii=False)
    except TypeError:
        s = str(obj)
    return s if len(s) <= limit else s[: limit - 1] + "…"


def log(actor: dict, action: str, input=None, output=None, verdict=None,
        citation=None, status="ok"):
    with session() as con:
        con.execute(
            """INSERT INTO audit_log(ts, actor, role, org, action, input, output,
               verdict, citation, status) VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (now(), actor.get("name"), actor.get("role"), actor.get("org"), action,
             _short(input), _short(output), verdict, citation, status))


def audited(action: str, summarize_input=None, summarize_output=None):
    """Decorator for functions whose first argument is the acting user."""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(actor, *args, **kwargs):
            inp = summarize_input(*args, **kwargs) if summarize_input else (
                {"args": [a for a in args if not isinstance(a, (bytes, bytearray))],
                 **{k: v for k, v in kwargs.items() if not isinstance(v, (bytes, bytearray))}})
            try:
                result = fn(actor, *args, **kwargs)
            except PermissionError:
                raise  # already logged as 'denied' by auth.require
            except Exception as e:
                log(actor, action, inp, {"error": str(e)}, status="error")
                raise
            out = summarize_output(result) if summarize_output else result
            verdict = result.get("verdict") if isinstance(result, dict) else None
            citation = result.get("citation") if isinstance(result, dict) else None
            log(actor, action, inp, out, verdict=verdict, citation=citation)
            return result
        return wrapper
    return deco


def fetch(actor: dict, limit=500) -> list:
    """Audit rows the actor may see: admin all, pharmacist own org, household own."""
    role = actor.get("role")
    q, params = "SELECT * FROM audit_log", []
    if role == "pharmacist":
        q += " WHERE org = ?"; params.append(actor.get("org"))
    elif role == "household":
        q += " WHERE actor = ?"; params.append(actor.get("name"))
    q += " ORDER BY id DESC LIMIT ?"; params.append(limit)
    with session() as con:
        return [dict(r) for r in con.execute(q, params)]

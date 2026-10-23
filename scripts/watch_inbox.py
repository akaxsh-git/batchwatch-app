"""Scheduler: watch data/inbox for newly published alert files.

    python scripts/watch_inbox.py              # checks every 6 hours
    python scripts/watch_inbox.py --every 1m   # faster, for a demo

When a new monthly file appears, the agent parses and validates it and leaves it
*pending* for an admin, so the human gate is never skipped. Approving it in the app
triggers the re-check of every saved inventory and cabinet.
(In production, a fetch step would first download new PDFs from CDSCO into the inbox.)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apscheduler.schedulers.blocking import BlockingScheduler  # noqa: E402

from core import db, ingest  # noqa: E402
from core.db import SYSTEM  # noqa: E402
from core.notify import notify  # noqa: E402


def check_inbox():
    db.init_db()
    new = ingest.scan_inbox()
    for p in new:
        r = ingest.ingest_file(SYSTEM, p)
        notify(recipient=None, org="BatchWatch Compliance", verdict="POSSIBLE", ref=f"ingest:{r['ingest_id']}",
               message=f"New alert file {p.name}: {r['rows']} rows, validation {r['validation']}. Awaiting your approval.")
        print(f"ingested {p.name}: {r['rows']} rows, validation {r['validation']} (pending approval)")
    if not new:
        print("inbox: nothing new")


if __name__ == "__main__":
    every = "6h"
    if "--every" in sys.argv:
        every = sys.argv[sys.argv.index("--every") + 1]
    unit = {"m": "minutes", "h": "hours"}[every[-1]]
    check_inbox()
    sched = BlockingScheduler()
    sched.add_job(check_inbox, "interval", **{unit: int(every[:-1])})
    print(f"Watching data/inbox every {every}. Ctrl+C to stop.")
    sched.start()

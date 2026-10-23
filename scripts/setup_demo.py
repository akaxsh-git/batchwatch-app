"""Create the database, demo users, and load the reviewed alert PDFs.

    python scripts/setup_demo.py           # first-time setup (~30 s)
    python scripts/setup_demo.py --reset   # wipe and start the demo again

Files in data/alerts are ingested and approved by the demo admin.
Files in data/inbox are left for the live "new month arrives" demo.
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import db, ingest  # noqa: E402
from core.paths import ALERTS_DIR, INBOX_DIR, db_path  # noqa: E402

DEMO_INBOX_MONTH = "2026-08"


def main():
    if "--reset" in sys.argv:
        p = db_path()
        if p.exists():
            p.unlink()
        # put the "new month" files back in the inbox for the demo
        for f in Path(ALERTS_DIR).glob(f"{DEMO_INBOX_MONTH}_*.pdf"):
            shutil.move(str(f), str(Path(INBOX_DIR) / f.name))
        print("Reset: database removed, August files returned to inbox.")
    db.init_db()
    db.seed_users()
    admin = db.get_user("Priya (Compliance Admin)")
    for pdf in sorted(Path(ALERTS_DIR).glob("*.pdf")):
        if pdf.name in ingest.known_files():
            continue
        r = ingest.ingest_file(admin, pdf)
        ok = r["validation"] == "passed"
        print(f"  {pdf.name:24} {r['rows']:4d} rows  validation {r['validation']}")
        if ok:
            ingest.approve(admin, r["ingest_id"], run_recheck=False)
    s = ingest.stats()
    print(f"Live alert rows: {s['live_rows']} ({s['first']} to {s['last']}), by list: {s['by_type']}")
    print(f"Waiting in inbox for the demo: {[p.name for p in ingest.scan_inbox()]}")


if __name__ == "__main__":
    main()

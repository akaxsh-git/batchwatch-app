"""Measure the numbers for the presentation (slide 'Measurable business value').

    python scripts/measure.py

Uses a temporary database, so it does not touch your demo data.
"""
import os
import random
import string
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["BATCHWATCH_DB"] = os.path.join(tempfile.mkdtemp(), "measure.db")

import pandas as pd  # noqa: E402

from core import db, ingest, stock  # noqa: E402
from core.matcher import match  # noqa: E402
from core.paths import ALERTS_DIR, INBOX_DIR  # noqa: E402

db.init_db(); db.seed_users()
admin = db.get_user("Priya (Compliance Admin)")
pharm = db.get_user("Ravi (Pharmacist)")

files = sorted(list(Path(ALERTS_DIR).glob("*.pdf")) + list(Path(INBOX_DIR).glob("*.pdf")))
t0 = time.perf_counter()
per_month = {}
for f in files:
    t = time.perf_counter()
    r = ingest.ingest_file(admin, f)
    ingest.approve(admin, r["ingest_id"], run_recheck=False)
    per_month[f.name[:7]] = per_month.get(f.name[:7], 0) + time.perf_counter() - t
total = time.perf_counter() - t0
s = ingest.stats()
print(f"Alert ingest: {len(files)} PDFs, {s['live_rows']} rows in {total:.1f} s "
      f"(avg {total/len(per_month):.1f} s per month of alerts)")

demo = pd.read_csv(ROOT / "data/demo/inventory_sunrise_pharmacy_demo.csv")
r = stock.check_inventory(pharm, demo)
print(f"Stock check: {r['lines']} lines in {r['seconds']} s -> {r['counts']}")
big = pd.concat([demo] * 10, ignore_index=True)
r = stock.check_inventory(pharm, big)
print(f"Stock check: {r['lines']} lines in {r['seconds']} s")

# matcher accuracy on real alert rows
import sqlite3  # noqa: E402
con = sqlite3.connect(os.environ["BATCHWATCH_DB"]); con.row_factory = sqlite3.Row
rows = con.execute("SELECT * FROM alerts WHERE length(batch_norm) >= 5").fetchall()
random.seed(7)
sample = random.sample(rows, 200)
ok = sum(match(a["batch"], a["product"], " ".join(a["manufacturer"].split()[:3]))["verdict"] == "FLAGGED" for a in sample)
ocr = [a for a in sample if "0" in a["batch_norm"]]
ocr_ok = sum(match(a["batch_norm"].replace("0", "O", 1), a["product"])["verdict"] == "POSSIBLE" for a in ocr)
wrong = sum(match(a["batch"], "Vitamin C Chewable Tablets", "Demo Nutrition Labs")["verdict"] == "FLAGGED" for a in sample)
known = {a["batch_norm"] for a in rows}
fakes = []
while len(fakes) < 500:
    f = "".join(random.choices(string.ascii_uppercase, k=2)) + "".join(random.choices(string.digits, k=6))
    if f not in known:
        fakes.append(f)
false_alarm = sum(match(f)["verdict"] != "CLEAR" for f in fakes)
print(f"Matcher: real alert rows flagged {ok}/{len(sample)}; OCR-misread versions caught as POSSIBLE "
      f"{ocr_ok}/{len(ocr)}; wrong-product cases flagged {wrong}/{len(sample)} (should be 0); "
      f"random batch numbers raising any alarm {false_alarm}/{len(fakes)}")

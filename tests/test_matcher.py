import random
import sqlite3
import string

from core.matcher import match
from core.paths import db_path


def _rows():
    con = sqlite3.connect(str(db_path())); con.row_factory = sqlite3.Row
    from core.matcher import PLACEHOLDER_BATCHES
    return [r for r in con.execute("SELECT * FROM alerts WHERE length(batch_norm) >= 5").fetchall()
            if r["batch_norm"] not in PLACEHOLDER_BATCHES]


def test_exact_batch_with_agreeing_name_is_flagged_with_citation():
    for a in random.Random(1).sample(_rows(), 40):
        r = match(a["batch"], a["product"], " ".join(a["manufacturer"].split()[:3]))
        assert r["verdict"] == "FLAGGED"
        assert r["citation"].startswith(a["source_file"]) or any(m["citation"].startswith(a["source_file"]) for m in r["matches"])


def test_ocr_lookalike_is_possible_not_silently_clear():
    rows = [a for a in _rows() if "0" in a["batch_norm"]][:30]
    for a in rows:
        assert match(a["batch_norm"].replace("0", "O", 1), a["product"])["verdict"] == "POSSIBLE"


def test_same_batch_on_unrelated_product_is_never_flagged():
    for a in _rows():
        assert match(a["batch"], "Vitamin C Chewable Tablets", "Demo Nutrition Labs")["verdict"] != "FLAGGED"


def test_random_batches_raise_no_alarm():
    rnd = random.Random(9)
    known = {a["batch_norm"] for a in _rows()}
    for _ in range(300):
        f = "".join(rnd.choices(string.ascii_uppercase, k=2)) + "".join(rnd.choices(string.digits, k=6))
        if f not in known:
            assert match(f)["verdict"] == "CLEAR"


def test_pending_data_is_not_used_until_approved(users):
    from conftest import TMP
    from core import ingest
    from core.matcher import invalidate
    q = ("18230791", "Telmisartan 40 mg and Amlodipine 5mg tablets")   # only in the August spurious list
    assert match(*q)["verdict"] == "CLEAR"
    r = ingest.ingest_file(users["admin"], TMP / "inbox" / "2026-08_spurious.pdf")
    invalidate()
    assert match(*q)["verdict"] == "CLEAR"  # still pending: not used
    ingest.approve(users["admin"], r["ingest_id"], run_recheck=False)
    assert match(*q)["verdict"] == "FLAGGED"

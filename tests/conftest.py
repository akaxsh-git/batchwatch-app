"""Test fixtures: an isolated database and folders, loaded with a few real alert PDFs."""
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TMP = Path(tempfile.mkdtemp(prefix="batchwatch_test_"))
os.environ["BATCHWATCH_DB"] = str(TMP / "test.db")
os.environ["BATCHWATCH_ALERTS_DIR"] = str(TMP / "alerts")
os.environ["BATCHWATCH_INBOX_DIR"] = str(TMP / "inbox")
os.environ["BATCHWATCH_OFFLINE"] = "1"
sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402

SRC = {"alerts": ["2026-03_central.pdf", "2026-04_state.pdf", "2026-05_spurious.pdf"],
       "inbox": ["2026-08_central.pdf", "2026-08_spurious.pdf"]}


def _find(name):
    for d in (ROOT / "data/alerts", ROOT / "data/inbox"):
        if (d / name).exists():
            return d / name
    raise FileNotFoundError(name)


@pytest.fixture(scope="session", autouse=True)
def loaded_db():
    for folder, names in SRC.items():
        (TMP / folder).mkdir(parents=True, exist_ok=True)
        for n in names:
            shutil.copy(_find(n), TMP / folder / n)
    from core import db, ingest
    db.init_db(); db.seed_users()
    admin = db.get_user("Priya (Compliance Admin)")
    for f in sorted((TMP / "alerts").glob("*.pdf")):
        r = ingest.ingest_file(admin, f)
        ingest.approve(admin, r["ingest_id"], run_recheck=False)
    yield
    shutil.rmtree(TMP, ignore_errors=True)


@pytest.fixture
def users():
    from core import db
    return {k: db.get_user(n) for k, n in [("admin", "Priya (Compliance Admin)"), ("pharm", "Ravi (Pharmacist)"),
                                           ("pharm2", "Anita (Pharmacist)"), ("home", "Meera (Household)")]}

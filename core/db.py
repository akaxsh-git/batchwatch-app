"""SQLite storage. One file, no server, works offline."""
import sqlite3
from contextlib import contextmanager

from .paths import db_path

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin','pharmacist','household')),
    org TEXT
);

-- one row per alert PDF ingested; only 'live' ingests are used for matching
CREATE TABLE IF NOT EXISTS ingests (
    id INTEGER PRIMARY KEY,
    source TEXT, source_file TEXT UNIQUE, alert_month TEXT, list_type TEXT,
    sha256 TEXT, rows INTEGER, max_sno INTEGER, missing TEXT,
    validation TEXT CHECK (validation IN ('passed','failed')),
    status TEXT CHECK (status IN ('pending','live','rejected')),
    ingested_by TEXT, ingested_at TEXT, reviewed_by TEXT, reviewed_at TEXT
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY,
    ingest_id INTEGER REFERENCES ingests(id),
    alert_month TEXT, list_type TEXT, source_file TEXT, page INTEGER, sno INTEGER,
    product TEXT, batch TEXT, batch_norm TEXT, mfg_date TEXT, exp_date TEXT,
    manufacturer TEXT, nsq_result TEXT, reporting_source TEXT,
    reporting_lab_state TEXT, reporting_month TEXT, remarks TEXT
);
CREATE INDEX IF NOT EXISTS idx_alerts_batch ON alerts(batch_norm);

CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY,
    org TEXT NOT NULL, sku TEXT, product TEXT, batch TEXT, manufacturer TEXT,
    qty INTEGER, supplier TEXT, supplier_email TEXT,
    verdict TEXT, citation TEXT, alert_id INTEGER, checked_at TEXT,
    status TEXT DEFAULT 'in_stock' CHECK (status IN ('in_stock','quarantined'))
);

CREATE TABLE IF NOT EXISTS cabinet (
    id INTEGER PRIMARY KEY,
    owner TEXT NOT NULL, product TEXT, batch TEXT, manufacturer TEXT, expiry TEXT,
    verdict TEXT, citation TEXT, alert_id INTEGER, added_at TEXT, checked_at TEXT
);

-- drafts the agent prepares; nothing leaves the system without approval
CREATE TABLE IF NOT EXISTS actions (
    id INTEGER PRIMARY KEY,
    kind TEXT CHECK (kind IN ('supplier_return','controller_report')),
    owner TEXT, org TEXT, recipient TEXT, subject TEXT, body TEXT, items TEXT,
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft','approved','rejected')),
    created_at TEXT, decided_by TEXT, decided_at TEXT
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY,
    recipient TEXT, org TEXT, message TEXT, verdict TEXT, ref TEXT,
    created_at TEXT, read INTEGER DEFAULT 0
);

-- append-only audit trail of every action, by every user and the agent
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY,
    ts TEXT, actor TEXT, role TEXT, org TEXT, action TEXT,
    input TEXT, output TEXT, verdict TEXT, citation TEXT,
    status TEXT CHECK (status IN ('ok','denied','error'))
);
"""


def connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path), timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


@contextmanager
def session():
    con = connect()
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db():
    with session() as con:
        con.executescript(SCHEMA)


DEMO_USERS = [
    ("Priya (Compliance Admin)", "admin", "BatchWatch Compliance"),
    ("Ravi (Pharmacist)", "pharmacist", "Sunrise Pharmacy (Demo)"),
    ("Anita (Pharmacist)", "pharmacist", "CarePlus Hospital Pharmacy (Demo)"),
    ("Meera (Household)", "household", None),
]


def seed_users():
    with session() as con:
        for name, role, org in DEMO_USERS:
            con.execute("INSERT OR IGNORE INTO users(name, role, org) VALUES (?,?,?)", (name, role, org))


def get_user(name: str) -> dict:
    with session() as con:
        r = con.execute("SELECT * FROM users WHERE name=?", (name,)).fetchone()
    if not r:
        raise KeyError(f"Unknown user {name}")
    return dict(r)


def list_users() -> list:
    with session() as con:
        return [dict(r) for r in con.execute("SELECT * FROM users ORDER BY id")]


SYSTEM = {"name": "BatchWatch Agent", "role": "system", "org": None}

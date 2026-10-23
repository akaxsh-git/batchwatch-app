"""File locations. Override the database path with BATCHWATCH_DB (used by tests)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ALERTS_DIR = Path(os.getenv("BATCHWATCH_ALERTS_DIR", str(DATA / "alerts")))  # reviewed alert PDFs
INBOX_DIR = Path(os.getenv("BATCHWATCH_INBOX_DIR", str(DATA / "inbox")))     # newly published, not yet ingested
DEMO_DIR = DATA / "demo"
SOURCES_DIR = ROOT / "sources"


def db_path() -> Path:
    return Path(os.getenv("BATCHWATCH_DB", str(DATA / "batchwatch.db")))

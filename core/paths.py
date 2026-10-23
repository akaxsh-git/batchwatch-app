"""File locations. Override the database path with BATCHWATCH_DB (used by tests)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ALERTS_DIR = DATA / "alerts"      # alert PDFs already reviewed
INBOX_DIR = DATA / "inbox"        # newly published alert PDFs waiting for ingest
DEMO_DIR = DATA / "demo"
SOURCES_DIR = ROOT / "sources"


def db_path() -> Path:
    return Path(os.getenv("BATCHWATCH_DB", str(DATA / "batchwatch.db")))

"""Measure label-reading accuracy with your Gemini key.

    python scripts/eval_labels.py                 # the demo labels
    python scripts/eval_labels.py path/to/photos  # your own photos + a truth.csv (file,batch)

Prints, per photo, the batch the AI read vs the truth, and the overall accuracy.
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent import llm  # noqa: E402
from core.parser import norm_batch  # noqa: E402

if llm.mode() != "gemini":
    sys.exit("Set GEMINI_API_KEY in .env first (this script measures the real AI).")

folder = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data/demo/labels"
if (folder / "truth.csv").exists():
    truth = {r["file"]: r["batch"] for r in csv.DictReader(open(folder / "truth.csv"))}
else:
    meta = json.loads((folder / "labels.json").read_text())
    truth = {k: v["printed"]["batch_number"] for k, v in meta.items() if "blurry" not in k}

right = 0
for name, batch in truth.items():
    r = llm.read_label((folder / name).read_bytes(), name)
    got = r["fields"].get("batch_number")
    ok = norm_batch(got or "") == norm_batch(batch)
    right += ok
    print(f"{'OK ' if ok else 'MISS'} {name:32} truth={batch:12} read={got} conf={r['confidence'].get('batch_number')}")
print(f"\nBatch numbers read exactly: {right}/{len(truth)} ({100*right/len(truth):.0f}%)")

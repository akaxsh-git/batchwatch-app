# BatchWatch

**An agent that checks pharmacy stock and household medicines against India's monthly drug-quality alerts, then acts, reports and keeps watching.**

AgentOps 2026 · Team **2B or Not 2B** (HX-2KCF) · Akash Ghosh
CGI business domain: **Healthcare / Life Sciences** · Track 04: Agents for Sustainable Development (SDG 3.8)

---

## The problem

Every month, CDSCO (India's drug regulator) publishes PDF lists of medicine batches that failed quality tests ("Not of Standard Quality") or were found to be spurious. From March to August 2026 these lists flagged **1,042 batches**, including common antibiotics and paracetamol. Selling or stocking these batches is prohibited (Drugs & Cosmetics Act, s.18), but checking hundreds of stock lines against ~170 new PDF rows a month is manual. Households have no practical way to check at all.

## What BatchWatch does

| Mode | Who | Flow |
|---|---|---|
| **Stock (B2B)** | Pharmacies, hospital pharmacies, distributors | Upload inventory CSV → every line checked → quarantine list with citations → supplier return drafts → pharmacist approves → compliance report |
| **Household (B2C)** | Patients, caregivers | Photo of a strip → AI reads the batch → user confirms → verdict with plain-language explanation → optional report to the drug controller → saved to a medicine cabinet |
| **Monthly loop** | Everyone | New alert file arrives → admin approves → agent re-checks every saved inventory and cabinet → notifies only on changes |

**Design rule: the LLM never decides whether a batch is flagged.** It reads labels, plans, explains and drafts. The verdict comes from deterministic, tested code, and every flag cites the source file, serial number and page.

---

## Setup (macOS / Linux / Windows)

Requires **Python 3.10+**.

```bash
git clone <your-repo-url> batchwatch && cd batchwatch
python3 -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env                # then put your Gemini key in .env (optional, see below)
python scripts/setup_demo.py        # builds the database from the alert PDFs (~30 s)
streamlit run app.py                # opens http://localhost:8501
```

**Gemini key (optional).** Get one free at [aistudio.google.com](https://aistudio.google.com) and set `GEMINI_API_KEY` in `.env`. Without a key, the app runs in **offline fallback mode**: demo labels are read from `data/demo/labels/labels.json`, other photos via Tesseract OCR if installed (`brew install tesseract`), or by typing the batch number. Explanations and drafts use rule-based templates. Everything else is identical. Set `BATCHWATCH_OFFLINE=1` to force this mode (e.g. bad Wi-Fi during a demo).

**Reset the demo** at any time: `python scripts/setup_demo.py --reset` (puts the August files back in the inbox).
Approving files moves them from `data/inbox/` to `data/alerts/`, so **run the reset before every demo and before your final commit**, then check `git status` is clean.

---

## Deployment (Streamlit Community Cloud)

BatchWatch is fully prepared for one-click deployment on [Streamlit Community Cloud](https://share.streamlit.io):

1. **Push your repository to GitHub** (keep your `.env` ignored; never commit keys).
2. Go to **[share.streamlit.io](https://share.streamlit.io)** and click **New app**.
3. Configure the app settings:
   - **Repository**: `your-username/batchwatch-app`
   - **Branch**: `main` (or `design-polish`)
   - **Main file path**: `app.py`
4. Expand **Advanced settings** $\rightarrow$ **Secrets**, and enter your Gemini API key:
   ```toml
   GEMINI_API_KEY = "your-gemini-api-key"
   GEMINI_MODEL = "gemini-2.5-flash"
   ```
5. Click **Deploy!**
   - **Zero manual database setup**: On first launch, `ui.ensure_db()` automatically bootstraps the database from bundled CDSCO alert PDFs and seeds the demo users.
   - If the API key secret is omitted, the app automatically operates in offline fallback mode with deterministic rule-based explanations.

---

## 5-minute demo script

Switch users with **"Signed in as (demo)"** in the sidebar. Each role sees different pages.

1. **Priya (Compliance Admin) → Home.** 821 live alert batches (Mar–Jul 2026); 3 new files in the inbox.
2. **Ravi (Pharmacist) → Stock check → "Use demo inventory".** 200 lines checked in a fraction of a second: 8 FLAGGED, 2 POSSIBLE. Open *Agent steps*. Review the drafts → **Apply my decisions**. Download the compliance report.
3. **Meera (Household) → Scan a medicine → Demo labels.**
   - *cefixime flagged* → confirm batch → FLAGGED, flagged in 2 separate alerts, plain-language explanation, cited source → approve or decline the report.
   - *pantoprazole ocr slip* → AI is unsure (62%) and reads `BCV4OO1DZ` → POSSIBLE → user corrects to `BCV4001DZ` → FLAGGED. Shows the human gate catching an AI misread.
   - *telmisartan august* → **not in alerts** (yet). Saved to the cabinet.
   - *cefixime blurry* → unreadable → asks for a retake.
4. **Priya → Alert data → Ingest and validate → Approve** the three August files. The agent re-checks every saved item automatically.
5. **Meera → Home**: notification that her Telmisartan batch now appears in an alert. **Ravi → Home**: 3 newly flagged stock lines.
6. **Audit & reports**: every AI tool call, human decision and re-check, with who/when/verdict/citation. As Ravi, click **"Try to approve alert data"**: blocked, and logged as *denied*.

---

## How it works

```
CDSCO PDFs ──► parser ──► validation ──► [ADMIN APPROVES] ──► live alert DB ──► matcher ──► verdict + citation
 (inbox)       (cell boxes → rows)   (S.No 1..N, no gaps)                          ▲            │
                                                                                   │            ▼
 photo ──► read_label (Gemini) ──► [USER CONFIRMS BATCH] ─────────────────────────┘     explain / drafts
 inventory CSV ─────────────────────────────────────────────────────────────────────►  [HUMAN APPROVES]
                                                                                              │
 monthly: new approved file ──► re-check all saved items ──► notify on change ──► audit log + compliance report
```

### Agent (LangGraph), `agent/graphs.py`
- **Household graph:** `read_label → confirm_batch (pause) → match → explain → draft_report → approve_report (pause) → save`, with branches for *retake* (unreadable photo) and *recheck_strip* (POSSIBLE → user re-checks the pack, pause).
- **Stock graph:** `check → plan → draft_returns → approve (pause) → apply → report`.
- Pauses use LangGraph `interrupt()`; the UI resumes with the person's decision. Each step appends to a visible **trace**.

### Tools, `agent/tools.py`
`read_label` · `match_batch` · `explain_alert` · `draft_controller_report` · `draft_supplier_returns`, plus `check_inventory`, `ingest_alert_file`, `recheck`. Every tool is permission-checked and audited.

### Verdicts, `core/matcher.py`
| Verdict | Rule |
|---|---|
| **FLAGGED** | exact batch match **and** product or manufacturer agrees (distinctive words only, ignoring "tablets", "IP", "Pvt Ltd") |
| **POSSIBLE** | OCR look-alike (0/O, 1/I, 5/S, 8/B, 2/Z), ≥ 90 % similar, or same batch on a different product → a person must check |
| **NOT IN ALERTS** | nothing close in *approved* data. Never shown as "safe" |

### Parser, `core/parser.py`
CDSCO tables are drawn as shaded cell rectangles. The parser groups rectangles sharing a top/bottom edge into rows, places each word in its cell, maps columns from the header row (config in `sources/cdsco.yaml`), merges rows that spill across page breaks, and normalises batch numbers. A file only goes live if serial numbers run 1..N with no gaps.

---

## Responsible AI & governance

| Control | Where |
|---|---|
| **Explainability** | Every verdict cites `file · S.No · page`; explanations use only that row; agent steps shown in the UI |
| **Human approval** | Admin approves new data · user confirms the batch read · POSSIBLE needs a person · returns and reports sent only after approval |
| **Audit trail** | `audit_log` table: every tool call, AI reading, human decision, re-check and denied attempt. Exportable CSV |
| **Role-based access** | `core/auth.py`, enforced in the backend: admin / pharmacist (own org only) / household (own data only) / system |
| **Authentication note** | Landing page role picker is for demonstration; production deployments require enterprise SSO (OAuth 2.0 / SAML) or hashed credentials. Backend RBAC is strictly enforced. |
| **Privacy & security** | Only the label image goes to the LLM (no names or inventories); photos dropped after reading; keys only in `.env` (git-ignored). Production: Gemini paid tier, where inputs aren't used for training |
| **Fail-safe wording** | "Not in published alerts", never "safe"; "speak to your pharmacist or doctor", never "stop taking"; LLM output containing dosing or stop/continue advice is replaced by the rule-based text |

## Reusability

The only CDSCO-specific part is `sources/cdsco.yaml` (file pattern + column keywords). To support another regulator's alert list (food-safety recalls, medical-device alerts, US FDA recalls, EU Safety Gate, automotive part recalls), add a new YAML file. The parser, matcher, agent graphs, audit log, roles and UI are reused unchanged.

---

## Tests and measurements

```bash
python -m pytest -q          # 18 tests: parser, matcher, governance/RBAC, audit, agent graphs, re-check
python scripts/measure.py    # numbers for the presentation
python scripts/eval_labels.py   # label-reading accuracy with your Gemini key
python scripts/watch_inbox.py --every 1m   # scheduler: auto-ingests new files in data/inbox as *pending*
```

Measured on the bundled data (Linux laptop-class CPU):

| Metric | Result |
|---|---|
| Alert ingest | 17 PDFs, 1,042 rows in ~37 s (~6 s per month of alerts) |
| Stock check | 200 lines in 0.17 s · 2,000 lines in 1.4 s |
| Real alert rows flagged | 200 / 200 |
| OCR-misread batches caught as POSSIBLE | 133 / 133 |
| Same batch on an unrelated product flagged | 0 / 200 |
| Random batch numbers raising any alarm | 0 / 500 |

## Project structure

```
app.py                Streamlit entry; role-based navigation
ui.py                 shared UI helpers
views/                home · admin (alert data) · pharmacy (stock) · household (scan) · audit
agent/                llm.py (Gemini + offline fallback) · tools.py · graphs.py (LangGraph)
core/                 parser · ingest · matcher · stock · cabinet · recheck · actions · report · audit · auth · notify · db
sources/cdsco.yaml    source adapter config
scripts/              setup_demo · make_demo_data · measure · eval_labels · watch_inbox
data/alerts/          CDSCO alert PDFs Mar–Jul 2026 (loaded at setup)
data/inbox/           CDSCO alert PDFs Aug 2026 ("new month" for the demo)
data/demo/            fictional inventories + DEMO label images
tests/                pytest suite
```

## Data and limitations

- **Alert data:** CDSCO monthly NSQ / spurious drug alert lists, March–August 2026, public documents. Downloaded from a public mirror (TheHealthMaster) because CDSCO's NSQ section blocks automated downloads; file titles were checked. In production, a fetch step would download directly from CDSCO into `data/inbox/`.
- **Demo data** (`data/demo/`) is **fictional**: pharmacy names, suppliers and label images are made up and marked DEMO. Only the alert batches mixed into them are real.
- Alerts cover only batches that were sampled and tested; "not in alerts" is not a quality certificate.
- The agent's checkpoints are in memory (fine for a demo); production would use a persistent checkpointer.

## Licences

Code: MIT. Libraries: Streamlit (Apache-2.0), LangGraph (MIT), google-genai (Apache-2.0), pdfplumber (MIT), RapidFuzz (MIT), pandas (BSD-3), PyYAML (MIT), APScheduler (MIT), Pillow (MIT-CMU).

# Use Case 3 — AP Invoice Matching (Accounts Payable)

Automates AP invoice control: run a **3-way match** of a supplier **invoice**
against its **purchase order** and **goods receipt**. Clean matches auto-post and
mint a payment reference; anything with a variance (price, quantity, not-on-PO,
not-received) routes to a human review queue. A separate check flags goods that
were **received but never invoiced**.

## Stack
Python + **FastAPI** (endpoints) + **Streamlit** (UI) over plain **JSON files**
that stand in for the ERP's AP ledger. The 3-way match is pure Python (no LLM),
so it's deterministic and trivially testable. `python-dotenv` loads the shared
project `.env`.

## Layout
```
usecase3/
├─ config.py            # paths, thresholds, UC3_API_BASE_URL (loads .env)
├─ matcher.py           # match_invoice() — the 3-way match engine (pure Python)
├─ alert.py             # check_received_not_invoiced() — accrual/missing-invoice risk
├─ store.py             # tiny defensive JSON read/write/append helpers
├─ ui.py                # Streamlit UI (render() hub entry) — thin client over the API
├─ api/
│  ├─ main.py           # FastAPI app + the 4 /uc3 endpoints (+ /health, CORS)
│  ├─ schemas.py        # Pydantic request models (Flag / Post)
│  └─ runtime.py        # auto-start uvicorn from Streamlit (port 8001)
└─ data/
   ├─ receipts.json           # goods receipts (mock)
   ├─ flagged_invoices.json   # review queue (starts [])
   ├─ posted_invoices.json    # approved + paid ledger (starts [])
   └─ samples.json            # demo POs / receipts / invoices for the match panel
```

## Quick start
```bash
streamlit run Home.py        # hub auto-starts the API (:8001) → open "AP Invoice Matching"
# or run the API on its own:
uvicorn usecases.usecase3.api.main:app --reload --port 8001   # docs at /docs
```

The Streamlit UI has three tabs: **Match Invoice** (pick a sample → 3-way match →
post or flag), **Review Queue** (list + approve pending), and **Alerts**
(received-not-invoiced).

## The 3-way match (`matcher.match_invoice`)
For each invoice line it finds the matching PO line (by `part_number`) and receipt
line, then assigns a per-line status:

| Status | Meaning |
|---|---|
| `MATCH` | On the PO, received, price within tolerance, qty equals received |
| `PRICE_VARIANCE` | Invoice `unit_price` differs from PO price (beyond `0.01` tolerance) |
| `QTY_VARIANCE` | Invoice `quantity` differs from receipt `qty_received` |
| `NOT_ON_PO` | `part_number` is not on the purchase order |
| `NOT_RECEIVED` | On the PO but not on any goods receipt |

Overall: all lines `MATCH` → **`PERFECT_MATCH`** (`auto_approve: true`); otherwise
**`VARIANCE_FOUND`** (`auto_approve: false`). Returns
`{match_result, auto_approve, flags, line_results, po, receipt}`.

## API (base `http://localhost:8001`)
Interactive docs: `http://localhost:8001/docs`. Errors return `{"detail": "..."}`.

### `POST /uc3/flag-invoice`
Queue an invoice for human review (forces `status: "Pending Review"`, stamps `flagged_at`).
```jsonc
// request
{ "invoice_number":"INV-1002", "vendor_name":"PharmaCo Ltd", "po_number":"PO-2026-002",
  "total_amount":750.0, "match_result":{"match_result":"VARIANCE_FOUND"}, "status":"..." }
// 200
{ "status":"flagged",
  "invoice":{ "invoice_number":"INV-1002", "...":"...", "status":"Pending Review",
              "flagged_at":"2026-07-08 20:00:00" } }
```

### `GET /uc3/flagged-invoices`
Return the review queue (empty `[]` if the file doesn't exist yet).
```jsonc
[ { "invoice_number":"INV-1002", "vendor_name":"PharmaCo Ltd", "po_number":"PO-2026-002",
    "total_amount":750.0, "status":"Pending Review", "flagged_at":"2026-07-08 20:00:00" } ]
```

### `POST /uc3/post-invoice`
Post an approved invoice: mints a sequential `PAY-2026-#####` reference (from the
count in `posted_invoices.json`), appends it, and marks any matching flagged
record as `Posted`.
```jsonc
// request
{ "invoice_number":"INV-1001", "vendor":"MedSupply Corp", "po_number":"PO-2026-001",
  "invoice_amount":1650.0, "match_result":"PERFECT_MATCH", "status":null, "approved_by":"alice" }
// 200
{ "status":"posted", "payment_ref":"PAY-2026-00001", "flagged_updated":true,
  "invoice":{ "...":"...", "payment_ref":"PAY-2026-00001",
              "posted_at":"2026-07-08 20:00:00", "status":"Posted" } }
```

### `GET /uc3/check-alerts`
Goods received ≥ 30 days ago whose PO has no posted invoice (accrual risk).
```jsonc
[ { "receipt_id":"REC-2026-003", "vendor":"SurgTech Inc", "po_number":"PO-2026-003",
    "received_date":"2026-06-01", "days_overdue":37 } ]
```

### `GET /health`
`{ "status":"ok" }` — liveness probe used by the Streamlit auto-start.

## Config (`config.py`)
| Setting | Default | Purpose |
|---|---|---|
| `UC3_API_BASE_URL` | `http://localhost:8001` | Backend URL (own port so it coexists with UC1's `:8000`) |
| `PRICE_MATCH_TOLERANCE` | `0.01` | Allowed unit-price difference before flagging `PRICE_VARIANCE` |
| `RECEIVED_NOT_INVOICED_THRESHOLD_DAYS` | `30` | Age at which a received-not-invoiced receipt alerts |

Data lives in `usecases/usecase3/data/`; paths are anchored to the package (not
the process CWD), so it works no matter where uvicorn/Streamlit is launched from.

## Notes
- Self-contained and independent of UC1/UC2 — nothing here imports or modifies them.
- `Home.py` starts this API (`:8001`) alongside UC1's (`:8000`) on launch, so a
  single `streamlit run Home.py` brings the whole suite up.
- The match panel is driven by `data/samples.json`; the spec'd `receipts.json`,
  `flagged_invoices.json`, and `posted_invoices.json` are the live ledgers the
  endpoints read and write.

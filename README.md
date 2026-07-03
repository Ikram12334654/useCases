# Use Case Suite

A collection of AI-assisted business-automation demos, served as a single
Streamlit **hub** app. Each use case is a self-contained service (a package
under `usecases/`) exposing a `render()` UI, wired into the hub as a page.

Run once, navigate between use cases from the sidebar:

```powershell
pip install -r requirements.txt
copy .env.example .env          # then edit .env and add your real OPENAI_API_KEY
streamlit run Home.py
```

## Structure

```
Home.py                       Landing hub (entry point) — lists the use cases
pages/                        One thin wrapper per use case (Streamlit nav)
  1_Sales_Order_Entry.py        set_page_config → usecases.sales_order.ui.render()
  2_Use_Case_2.py               placeholder
  3_Use_Case_3.py               placeholder
usecases/
  __init__.py                 USE_CASES registry (drives the hub cards)
  sales_order/                Use Case 1 — live
    ui.py                       Streamlit UI, exposes render()
    extractor.py                PDF/text/image → OpenAI → structured JSON
    matcher.py                  fuzzy match vs data/*.json + price validation
    order_creator.py            mock D365 order + persists to orders.json
    data/                       customers.json, products.json (mock ERP master data)
    orders.json                 audit log of created orders (runtime)
  usecase2/ui.py              Use Case 2 — placeholder
  usecase3/ui.py              Use Case 3 — placeholder
shared/
  config.py                   load .env once + get_openai_client(), OPENAI_MODEL
requirements.txt
```

`.env` (shared by all use cases):

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
```

## Adding a new use case

1. Create `usecases/<name>/ui.py` with a `def render() -> None:` function
   (plus any supporting modules — `extractor.py`, etc.).
2. Register it in `usecases/__init__.py` (`USE_CASES` list) so it appears on the
   hub landing page.
3. Add a wrapper `pages/N_<Name>.py`:

   ```python
   import streamlit as st
   st.set_page_config(page_title="...", page_icon="🧩", layout="wide")
   from usecases.<name>.ui import render
   render()
   ```

Use shared infrastructure via `from shared.config import get_openai_client, OPENAI_MODEL`.

---

## Use Case 1 — Automate Sales Order Entry from Emails and Documents

Submit a purchase order in any common format, extract it with OpenAI, match
against ERP master data (customers + products), review flags, and create a
**mock** Dynamics 365 F&O sales order — with a human approval step before
anything is created.

### Supported order formats

| Format | How it's handled |
|--------|------------------|
| **PDF attachment** (typed) | `pdfplumber` extracts text → OpenAI |
| **Typed email body** | pasted text → OpenAI (no attachment needed) |
| **Scanned document** | PDF with no text layer → rendered → OpenAI vision |
| **Handwritten / photo** | image upload (PNG/JPG) → OpenAI vision |

All four share the same OpenAI key and the same downstream matching / approval /
order-creation pipeline.

Two swaps from the original plan for Windows / Python 3.14 robustness:
- **rapidfuzz** instead of fuzzywuzzy + python-Levenshtein (clean wheels, no C build).
- **PyMuPDF** instead of pdf2image for PDF→image (no external Poppler binary).

> Extraction requires a valid OpenAI key. Matching and order creation are fully
> local and need no key.

### Matching & edge-case handling

- **Customer:** exact → fuzzy ≥80% (flag: name variation) → fuzzy 50–80% (flag:
  review) → no match (flag: new customer).
- **Product:** exact part number → fuzzy description ≥80% → weak fuzzy (flag) →
  unknown product (flag).
- **Pricing:** matches master → OK; differs → flag with the difference; missing
  or zero → falls back to master price (flagged).

### What is mocked vs. production

| Aspect | Demo | Production |
|--------|------|-----------|
| ERP master data | `data/*.json` | live D365 customer / item master |
| Order creation | `orders.json` file | D365 F&O OData API (`SalesOrderHeadersV2`) |
| Email intake | manual paste / upload | automated inbox monitor |
| Extraction | real (OpenAI) | same, + retry / rate-limit handling |

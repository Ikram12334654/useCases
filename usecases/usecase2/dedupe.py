"""dedupe.py — payment idempotency (duplicate-remittance protection).

A payment must only ever be applied ONCE. If the same remittance is processed
again (customer re-emails it, a batch is re-run), re-applying it would wrongly
reduce the open balance — money the customer never paid twice. This computes a
stable **dedup key** for a payment so the pipeline can recognise one it has
already posted.

The key is COMPUTED from the payment's own contents (nothing external needed):
  - payment reference (check # / wire confirmation / lockbox batch id), if present
  - customer, total amount, date
  - the set of (invoice_no, amount_applied) it applies to

Same remittance → same key (duplicate caught). Two genuinely different payments
(different check numbers) → different keys.
"""

from __future__ import annotations

import hashlib
import json


def dedup_key(extracted: dict, customer_id: str | None = None) -> str:
    """Return a stable 16-char deduplication key for this payment."""
    invoices = sorted(
        (str(i.get("invoice_no", "")).upper(), round(float(i.get("amount_applied", 0) or 0), 2))
        for i in extracted.get("invoices", []) or []
    )
    parts = {
        "customer": (customer_id or extracted.get("customer") or "").strip().upper(),
        "total": round(float(extracted.get("total_amount", 0) or 0), 2),
        "date": (extracted.get("date") or "").strip(),
        "reference": (extracted.get("reference") or "").strip().upper(),
        "invoices": invoices,
    }
    raw = json.dumps(parts, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]

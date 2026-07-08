"""
alert.py — "received but not invoiced" exception detector.

Reads the mock goods-receipt ledger and the posted-invoice ledger and flags any
receipt whose PO has been sitting un-invoiced for at least ``threshold_days``.
This is the AP accrual / missing-invoice risk: goods are in the door but no
supplier invoice has been posted against them.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from .config import POSTED_INVOICES_PATH, RECEIPTS_PATH, RECEIVED_NOT_INVOICED_THRESHOLD_DAYS
from .store import read_json


def _parse_date(value: str) -> date | None:
    """Parse an ISO ``YYYY-MM-DD`` date, returning None if it can't be parsed."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def check_received_not_invoiced(
    threshold_days: int = RECEIVED_NOT_INVOICED_THRESHOLD_DAYS,
) -> list[dict[str, Any]]:
    """
    Return an alert per goods receipt that is (a) at least ``threshold_days`` old
    and (b) has no matching posted invoice for its PO number.

    Each alert: {receipt_id, vendor, po_number, received_date, days_overdue}.
    """
    receipts = read_json(RECEIPTS_PATH, default=[])
    posted = read_json(POSTED_INVOICES_PATH, default=[])

    invoiced_pos = {p.get("po_number") for p in posted if p.get("po_number")}
    today = date.today()

    alerts: list[dict[str, Any]] = []
    for receipt in receipts:
        po_number = receipt.get("po_number")
        received = _parse_date(receipt.get("received_date"))
        if received is None:
            continue

        days_overdue = (today - received).days
        if days_overdue >= threshold_days and po_number not in invoiced_pos:
            alerts.append(
                {
                    "receipt_id": receipt.get("receipt_id"),
                    "vendor": receipt.get("vendor"),
                    "po_number": po_number,
                    "received_date": receipt.get("received_date"),
                    "days_overdue": days_overdue,
                }
            )

    return alerts


if __name__ == "__main__":
    import json

    print(json.dumps(check_received_not_invoiced(), indent=2))

"""
matcher.py — 3-way AP invoice match (invoice ↔ purchase order ↔ goods receipt).

Given an extracted invoice, the matching PO, and the matching goods receipt,
compare every invoice line on price (vs the PO) and quantity (vs the receipt)
and produce a per-line status plus an overall verdict. Pure Python — no I/O and
no LLM — so it's trivially testable and deterministic.

Line statuses
-------------
MATCH           part on the PO, received, price within tolerance, qty equals received
PRICE_VARIANCE  invoice unit_price differs from PO unit_price (beyond tolerance)
QTY_VARIANCE    invoice quantity differs from receipt qty_received
NOT_ON_PO       part_number is not on the purchase order
NOT_RECEIVED    part_number is on the PO but not on any goods receipt

Overall
-------
PERFECT_MATCH   every line is MATCH            -> auto_approve = True
VARIANCE_FOUND  at least one line is not MATCH -> auto_approve = False
"""

from __future__ import annotations

from typing import Any

from .config import PRICE_MATCH_TOLERANCE


def _norm_part(part_number: Any) -> str:
    """Canonicalize a part number for comparison (str, trimmed, lowercased)."""
    if part_number is None:
        return ""
    return str(part_number).strip().lower()


def _find_by_part(part: str, lines: list[dict[str, Any]]) -> dict[str, Any] | None:
    """First line in ``lines`` whose part_number matches ``part`` (already normalized)."""
    if not part:
        return None
    for line in lines or []:
        if _norm_part(line.get("part_number")) == part:
            return line
    return None


def match_invoice(
    invoice: dict[str, Any],
    purchase_orders: list[dict[str, Any]],
    receipts: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Run the 3-way match for one invoice.

    Returns:
        {
          match_result:  "PERFECT_MATCH" | "VARIANCE_FOUND",
          auto_approve:  bool,
          flags:         [str, ...],          # human-readable variance notes
          line_results:  [ {part_number, status, ...}, ... ],
          po:            <matched PO dict or {}>,
          receipt:       <matched receipt dict or {}>,
        }
    """
    po_number = invoice.get("po_number")

    # Find the PO and the goods receipt for this invoice's PO number.
    po = next((p for p in purchase_orders or [] if p.get("po_number") == po_number), None)
    receipt = next((r for r in receipts or [] if r.get("po_number") == po_number), None)

    po_lines = (po or {}).get("line_items", []) or []
    receipt_lines = (receipt or {}).get("line_items", []) or []

    line_results: list[dict[str, Any]] = []
    flags: list[str] = []

    for item in invoice.get("line_items", []) or []:
        part = _norm_part(item.get("part_number"))
        inv_qty = item.get("quantity")
        inv_price = item.get("unit_price")

        po_line = _find_by_part(part, po_lines)
        rec_line = _find_by_part(part, receipt_lines)

        po_price = po_line.get("unit_price") if po_line else None
        received_qty = rec_line.get("qty_received") if rec_line else None

        result: dict[str, Any] = {
            "part_number": item.get("part_number"),
            "description": item.get("description"),
            "invoice_qty": inv_qty,
            "received_qty": received_qty,
            "invoice_unit_price": inv_price,
            "po_unit_price": po_price,
            "status": "MATCH",
            "flag": None,
        }

        if po_line is None:
            # Can't price-check a part that isn't on the PO — hard exception.
            result["status"] = "NOT_ON_PO"
            result["flag"] = f"Part '{item.get('part_number')}' is not on PO {po_number}"
        elif rec_line is None:
            # On the PO but nothing received against it yet.
            result["status"] = "NOT_RECEIVED"
            result["flag"] = (
                f"Part '{item.get('part_number')}' on PO {po_number} has not been received"
            )
        else:
            price_variance = (
                inv_price is not None
                and po_price is not None
                and abs(float(inv_price) - float(po_price)) > PRICE_MATCH_TOLERANCE
            )
            qty_variance = (
                inv_qty is not None
                and received_qty is not None
                and float(inv_qty) != float(received_qty)
            )

            # Price variance takes precedence for the single status label; if the
            # line also has a quantity variance, both are surfaced in the flags.
            if price_variance:
                result["status"] = "PRICE_VARIANCE"
                result["flag"] = (
                    f"Price variance on '{item.get('part_number')}': "
                    f"invoice {inv_price} vs PO {po_price}"
                )
                if qty_variance:
                    result["flag"] += (
                        f"; quantity variance: invoiced {inv_qty} vs received {received_qty}"
                    )
            elif qty_variance:
                result["status"] = "QTY_VARIANCE"
                result["flag"] = (
                    f"Quantity variance on '{item.get('part_number')}': "
                    f"invoiced {inv_qty} vs received {received_qty}"
                )

        if result["flag"]:
            flags.append(result["flag"])
        line_results.append(result)

    if po is None:
        flags.insert(0, f"No purchase order found for {po_number}")
    if receipt is None:
        flags.insert(0, f"No goods receipt found for {po_number}")
    if not line_results:
        flags.append("No invoice line items to match")

    all_match = bool(line_results) and all(r["status"] == "MATCH" for r in line_results)
    match_result = "PERFECT_MATCH" if all_match else "VARIANCE_FOUND"
    auto_approve = all_match

    return {
        "match_result": match_result,
        "auto_approve": auto_approve,
        "flags": flags,
        "line_results": line_results,
        "po": po or {},
        "receipt": receipt or {},
    }


if __name__ == "__main__":
    import json
    import sys

    with open(sys.argv[1], "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    out = match_invoice(
        payload["invoice"],
        payload.get("purchase_orders", []),
        payload.get("receipts", []),
    )
    print(json.dumps(out, indent=2))

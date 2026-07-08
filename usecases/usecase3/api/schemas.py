"""
api/schemas.py — Pydantic request models for the Use Case 3 (AP) backend.

``match_result`` is whatever the matcher produced (usually the full match dict,
sometimes just a label string), so it's modeled as an open value rather than
re-declaring the matcher's shape here.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class FlagInvoiceRequest(BaseModel):
    """Route an invoice with variances into the human-review queue."""

    invoice_number: str
    vendor_name: str
    po_number: str
    total_amount: float
    match_result: Optional[Any] = Field(
        None, description="The matcher output (dict) or a summary label."
    )
    status: Optional[str] = Field(
        None, description="Ignored on flag — the server forces 'Pending Review'."
    )


class PostInvoiceRequest(BaseModel):
    """Approve + post an invoice to the (mock) AP ledger for payment."""

    invoice_number: str
    vendor: str
    po_number: str
    invoice_amount: float
    match_result: Optional[Any] = Field(
        None, description="The matcher output (dict) or a summary label."
    )
    status: Optional[str] = Field(None, description="Defaults to 'Posted' if omitted.")
    approved_by: str

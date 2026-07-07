"""decision.py — Module 5: confidence scoring + routing.

Assigns ``match_confidence`` per situation, applies the auto-post threshold, and
composes the ``recommendation`` payload the human sees (including a plain-English
proposed resolution for the long-tail cases). Exposes ``route_edge`` — the
LangGraph conditional-edge function.
"""

from __future__ import annotations

from ..config import AUTO_POST_CONFIDENCE_THRESHOLD
from ..db import payment_exists
from ..dedupe import dedup_key
from ..state import CashAppState
from .match import (
    AUTO_POSTABLE,
    CREDIT,
    DISPUTE,
    EXACT,
    EXCEPTION,
    MULTI_INVOICE,
    NO_REFERENCE,
    OVERPAY,
    PARTIAL,
    SHORT_PAY,
)

def _money(v) -> str:
    try:
        return f"${float(v):,.2f}"
    except (TypeError, ValueError):
        return str(v)


# Baseline confidence per situation (tunable; human decisions feed back later).
_SITUATION_CONFIDENCE = {
    EXACT: 1.0,
    PARTIAL: 0.7,
    CREDIT: 0.65,
    DISPUTE: 0.6,
    SHORT_PAY: 0.5,
    OVERPAY: 0.55,
    NO_REFERENCE: 0.5,
    MULTI_INVOICE: 0.55,
    EXCEPTION: 0.2,
}

# What the AI proposes doing for each situation (shown to the human).
_PROPOSED_ACTION = {
    EXACT: "Auto-post in full to the referenced invoice.",
    PARTIAL: "Post the paid amount; leave the invoice open for the remaining installment.",
    CREDIT: "Post the paid amount; open a CREDIT case for the deducted amount to reconcile against a credit memo.",
    DISPUTE: "Post the paid amount; open a dispute case for the withheld amount under its reason code.",
    SHORT_PAY: "Short paid with no stated reason — confirm with the customer or open an UNKNOWN dispute.",
    OVERPAY: "Post to the invoice; place the overpayment on account / open a credit.",
    NO_REFERENCE: "No invoice referenced — confirm the proposed allocation found by amount.",
    MULTI_INVOICE: "Confirm the proposed split across multiple invoices.",
    EXCEPTION: "No matching open invoice found — needs manual investigation.",
}


def decide(state: CashAppState) -> CashAppState:
    """Graph node: score, route, and build the recommendation."""
    mr = state["match_result"]
    extracted = state.get("extracted", {})
    situation = mr["situation"]
    extract_conf = float(state.get("extract_confidence", 0.0))
    match_conf = _SITUATION_CONFIDENCE.get(situation, 0.3)

    # Idempotency: has a payment with this dedup key already been applied?
    key = dedup_key(extracted, mr.get("customer_id"))
    existing = payment_exists(key)
    is_duplicate = existing is not None

    # Auto-post ONLY when: exact, no disputes, extraction confidence clears the
    # gate, AND this is not a duplicate remittance.
    auto = (
        situation in AUTO_POSTABLE
        and not mr.get("disputes")
        and extract_conf >= AUTO_POST_CONFIDENCE_THRESHOLD
        and not is_duplicate
    )
    route = "auto_post" if auto else "human_review"

    if is_duplicate:
        ref = existing.get("received_date") or existing.get("payment_id")
        proposed_action = (
            f"⚠️ DUPLICATE — a payment matching this remittance was already applied "
            f"(payment #{existing.get('payment_id')}, {_money(existing.get('amount'))} on {ref}). "
            f"Do NOT post again unless you can confirm this is a genuinely separate payment. "
            f"Recommended action: REJECT."
        )
    else:
        proposed_action = _PROPOSED_ACTION.get(situation, "Review.")

    recommendation = {
        "situation": situation,
        "route": route,
        "duplicate": is_duplicate,
        "existing_payment": existing,
        "dedup_key": key,
        "proposed_action": proposed_action,
        "match_confidence": match_conf,
        "extract_confidence": extract_conf,
        "proposed_allocation": mr.get("allocation", []),
        "proposed_disputes": mr.get("disputes", []),
        "lines": mr.get("lines", []),
        "gap": mr.get("gap"),
        "customer_id": mr.get("customer_id"),
        "payment": {
            "customer": extracted.get("customer"),
            "customer_id": mr.get("customer_id"),
            "total_amount": extracted.get("total_amount"),
            "currency": extracted.get("currency", "USD"),
            "date": extracted.get("date"),
            "channel": extracted.get("payment_channel"),
        },
        # the original document, so the review screen can display it
        "document_text": state.get("raw_text", ""),
        "document_images": state.get("images", []),
    }
    return {**state, "match_confidence": match_conf, "route": route, "recommendation": recommendation}


def route_edge(state: CashAppState) -> str:
    """LangGraph conditional edge: returns the next node key based on ``route``."""
    return state["route"]

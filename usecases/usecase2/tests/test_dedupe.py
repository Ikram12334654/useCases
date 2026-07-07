"""test_dedupe.py — payment idempotency (duplicate protection).

Dedup keys are pure; the DB lookup is exercised against a temp database so the
tests stay isolated from the demo mock_d365.db.
"""

from __future__ import annotations

from usecases.usecase2 import db as dbm
from usecases.usecase2.dedupe import dedup_key

_A = {
    "customer": "CUST001", "total_amount": 3000.0, "date": "2026-07-02", "reference": "CHK-40912",
    "invoices": [{"invoice_no": "INV-1002", "amount_applied": 3000.0}],
}


def test_same_document_same_key():
    assert dedup_key(_A, "CUST001") == dedup_key(dict(_A), "CUST001")


def test_different_reference_different_key():
    b = {**_A, "reference": "CHK-99999"}
    assert dedup_key(_A, "CUST001") != dedup_key(b, "CUST001")


def test_different_amount_different_key():
    b = {**_A, "total_amount": 3200.0}
    assert dedup_key(_A, "CUST001") != dedup_key(b, "CUST001")


def test_payment_exists_detects_duplicate(tmp_path):
    dbp = tmp_path / "t.db"
    dbm.init_db(dbp)
    key = dedup_key(_A, "CUST001")
    assert dbm.payment_exists(key, db_path=dbp) is None          # not yet applied
    dbm.record_payment("CUST001", 3000.0, dedup_key=key, db_path=dbp)
    assert dbm.payment_exists(key, db_path=dbp) is not None      # now detected
    assert dbm.payment_exists("nope", db_path=dbp) is None

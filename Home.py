"""
Home.py — Landing hub for the use-case suite.

Run:  streamlit run Home.py

Streamlit automatically turns every file in ``pages/`` into a sidebar nav entry.
This page is the entry point and lists the available use cases.
"""

from __future__ import annotations

import warnings

# Python 3.14 note: LangChain (UC2) still imports Pydantic v1 internally, which
# emits a "Core Pydantic V1 functionality isn't compatible with Python 3.14"
# UserWarning at import time. It's non-fatal; silence it here (process-wide,
# before any page imports LangChain) so the suite's output stays clean.
warnings.filterwarnings(
    "ignore",
    message=r"Core Pydantic V1 functionality isn't compatible with Python 3\.14.*",
)

import streamlit as st

from usecases import USE_CASES

st.set_page_config(page_title="Use Case Suite", page_icon="🗂️", layout="wide")


@st.cache_resource
def _start_backends() -> dict[str, bool]:
    """Boot the use-case FastAPI backends once per Streamlit session.

    Runs under cache_resource so it fires a single time (not on every rerun).
    Each start is best-effort: a backend that can't launch just reports False
    and the rest of the suite still loads. UC1 → :8000, UC3 → :8001.
    """
    from usecases.sales_order.api.runtime import ensure_api_running as start_uc1
    from usecases.usecase3.api.runtime import ensure_api_running as start_uc3

    status: dict[str, bool] = {}
    for name, starter in (("Sales Order API", start_uc1), ("AP Matching API", start_uc3)):
        try:
            status[name] = starter(timeout=20)
        except Exception:  # noqa: BLE001 — never let a backend break the landing page
            status[name] = False
    return status


_backends = _start_backends()

st.title("🗂️ Use Case Suite")
st.caption("A collection of AI-assisted business automation demos. Pick one to begin.")

st.divider()

# Page files, in nav order, so each card can deep-link to its use case.
_PAGE_PATHS = {
    "sales_order": "pages/1_Sales_Order_Entry.py",
    "usecase2": "pages/2_Use_Case_2.py",
    "usecase3": "pages/3_Use_Case_3.py",
}

_STATUS_BADGE = {"live": "🟢 Live", "in_progress": "🟡 In progress", "planned": "⚪ Planned"}

cols = st.columns(len(USE_CASES))
for col, uc in zip(cols, USE_CASES):
    with col:
        st.subheader(f"{uc['icon']} {uc['number']}. {uc['title']}")
        st.caption(uc["tagline"])
        st.write(_STATUS_BADGE.get(uc["status"], uc["status"]))
        page = _PAGE_PATHS.get(uc["key"])
        if page:
            st.page_link(page, label="Open →")

st.divider()
st.caption(
    "Add a new use case: create `usecases/<name>/ui.py` with a `render()` function, "
    "register it in `usecases/__init__.py`, and add a wrapper in `pages/`."
)

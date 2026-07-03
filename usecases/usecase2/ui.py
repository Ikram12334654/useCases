"""ui.py — Use Case 2 (placeholder).

Replace the body of `render()` with the real UI. Keep the same `render()`
signature so the hub page wrapper in ``pages/`` keeps working unchanged.
"""

from __future__ import annotations

import streamlit as st


def render() -> None:
    st.title("🧩 Use Case 2")
    st.info(
        "This use case is not built yet.\n\n"
        "To implement it, add your modules under `usecases/usecase2/` and replace "
        "the body of `render()` in this file. Shared config (OpenAI client, model) "
        "is available via `from shared.config import get_openai_client, OPENAI_MODEL`."
    )

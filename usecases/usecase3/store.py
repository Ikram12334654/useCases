"""store.py — tiny JSON-file persistence for UC3.

Stands in for the AP ledger the same way UC1's orders.json stands in for D365.
Every helper is defensive: a missing or corrupt file reads back as the default
(an empty list) rather than raising, and writes create the parent directory so
the very first flag/post call works on a clean checkout.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: str | Path, default: Any | None = None) -> Any:
    """Return the parsed JSON at ``path`` (empty list if missing/corrupt)."""
    fallback = [] if default is None else default
    p = Path(path)
    if not p.exists():
        return fallback
    try:
        with p.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return fallback


def write_json(path: str | Path, data: Any) -> None:
    """Write ``data`` as pretty JSON, creating parent dirs if needed."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)


def append_json(path: str | Path, record: dict[str, Any]) -> list[Any]:
    """Append ``record`` to the JSON list at ``path`` (creating it if absent)."""
    rows = read_json(path, default=[])
    if not isinstance(rows, list):
        rows = []
    rows.append(record)
    write_json(path, rows)
    return rows

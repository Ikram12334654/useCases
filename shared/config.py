"""
shared/config.py — Configuration and the OpenAI client shared by every use case.

Loads the single project-level .env once and hands out a configured client so
individual use cases don't each re-implement key handling.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")


def get_openai_client() -> OpenAI:
    """Return an OpenAI client, or raise a clear error if the key is missing."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return OpenAI(api_key=api_key)

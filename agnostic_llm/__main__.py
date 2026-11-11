"""Entry point for python -m agnostic_llm.
Supports standard raw model queries, interactive employee chat, web dashboard, and voice mode.
"""
from __future__ import annotations
import sys
from .cli import main

if __name__ == "__main__":
    main()

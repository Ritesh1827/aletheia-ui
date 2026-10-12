"""Central application configuration (mock-first, demo-labelled)."""

from __future__ import annotations

import os


def api_mode() -> str:
    return os.getenv("TRUSTTRACE_API_MODE", "mock").lower()


def is_demo() -> bool:
    return api_mode() == "mock"


def chain_label() -> str:
    return os.getenv("TRUSTTRACE_CHAIN_LABEL", "local demo network")


def app_title() -> str:
    return "TrustTrace · Oxide Observatory"

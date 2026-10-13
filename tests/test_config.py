"""Tests for application configuration (env vars, title)."""

from __future__ import annotations

import pytest

from app import config


def test_defaults_are_demo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ALETHEIA_API_MODE", raising=False)
    monkeypatch.delenv("ALETHEIA_CHAIN_LABEL", raising=False)
    assert config.api_mode() == "mock"
    assert config.is_demo() is True
    assert config.chain_label() == "local demo network"


def test_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALETHEIA_API_MODE", "live")
    monkeypatch.setenv("ALETHEIA_CHAIN_LABEL", "testnet")
    assert config.api_mode() == "live"
    assert config.is_demo() is False
    assert config.chain_label() == "testnet"


def test_title_is_aletheia() -> None:
    assert config.app_title().startswith("Aletheia")

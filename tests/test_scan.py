"""Tests for scan payload parsing + scanned verification wiring."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.scan_parse import parse_scan_payload


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False)


def test_plain_serial_passes_through() -> None:
    p = parse_scan_payload("AL-DEMO-0001")
    assert p.status == "serial"
    assert p.serial == "AL-DEMO-0001"


def test_plain_serial_case_insensitive() -> None:
    p = parse_scan_payload("  al-demo-0002  ")
    assert p.status == "serial"
    assert p.serial == "AL-DEMO-0002"


def test_structured_tt_payload() -> None:
    p = parse_scan_payload("AL:AL-DEMO-0001")
    assert p.status == "serial"
    assert p.serial == "AL-DEMO-0001"


def test_aletheia_url_with_serial_param() -> None:
    p = parse_scan_payload("https://verify.aletheia.example/v?serial=AL-DEMO-0002")
    assert p.status == "serial"
    assert p.serial == "AL-DEMO-0002"


def test_aletheia_url_path_serial() -> None:
    p = parse_scan_payload("https://verify.aletheia.example/p/AL-DEMO-0001")
    assert p.status == "serial"
    assert p.serial == "AL-DEMO-0001"


def test_foreign_url_with_serial_is_ambiguous() -> None:
    p = parse_scan_payload("https://evil.example/x?serial=AL-DEMO-0001")
    assert p.status == "ambiguous"
    assert p.serial == ""
    assert "AL-DEMO-0001" in p.candidates


def test_bare_url_without_serial_is_ambiguous() -> None:
    p = parse_scan_payload("https://example.com/some/page")
    assert p.status == "ambiguous"
    assert p.serial == ""


def test_garbage_payload_is_ambiguous() -> None:
    p = parse_scan_payload("!!! not a code !!!")
    assert p.status == "ambiguous"
    assert p.serial == ""


def test_empty_payload_is_ambiguous() -> None:
    p = parse_scan_payload("   ")
    assert p.status == "ambiguous"


def test_scanned_serial_verifies_end_to_end(client: TestClient) -> None:
    res = client.get("/verify", params={"q": "AL:AL-DEMO-0001"}, follow_redirects=False)
    assert res.status_code == 303
    assert res.headers["location"] == "/verify/AL-DEMO-0001"


def test_scanned_url_verifies_end_to_end(client: TestClient) -> None:
    res = client.get("/verify", params={"q": "https://verify.aletheia.example/v?serial=AL-DEMO-0002"},
                     follow_redirects=False)
    assert res.status_code == 303
    assert res.headers["location"] == "/verify/AL-DEMO-0002"


def test_ambiguous_payload_never_autoverifies(client: TestClient) -> None:
    res = client.get("/verify", params={"q": "https://evil.example/x?serial=AL-DEMO-0001"})
    assert res.status_code == 200
    assert "Unknown serial" in res.text
    assert "not auto-selected" in res.text


def test_verify_page_has_scan_button(client: TestClient) -> None:
    res = client.get("/verify")
    assert res.status_code == 200
    assert 'id="scan-open"' in res.text
    assert 'id="scan-modal"' in res.text
    assert "verify_scan.js" in res.text
    assert "Try a fixture" in res.text

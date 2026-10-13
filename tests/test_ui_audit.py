"""UI security-audit regressions (F1–F5).

F1: no server string interpolated into Alpine/JS string contexts.
F2: backend 4xx -> honest error page, never a 500; oversize serials rejected locally.
F4: red-team redirect is url-encoded and restricted to known fields.
F5: form/note length caps enforced.
"""

from __future__ import annotations

from urllib.parse import urlparse, parse_qs

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

XSS = "'},alert(document.domain),{x:'"


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False)


@pytest.fixture()
def clean_mock_lots() -> object:
    from app.services import mock_lots

    frozen = dict(mock_lots._FROZEN)
    recalled = dict(mock_lots._RECALLED)
    audit = {k: list(v) for k, v in mock_lots._AUDIT.items()}
    yield
    mock_lots._FROZEN.clear()
    mock_lots._FROZEN.update(frozen)
    mock_lots._RECALLED.clear()
    mock_lots._RECALLED.update(recalled)
    mock_lots._AUDIT.clear()
    mock_lots._AUDIT.update(audit)


def test_f1_no_js_string_breakout(client: TestClient) -> None:
    for url in (f"/explorer/search?q={XSS}", f"/verify?q={XSS}", f"/lots?q={XSS}"):
        r = client.get(url)
        assert r.status_code == 200, url
        # Invariant: no server-controlled string inside an x-data JS context...
        assert "x-data=\"{ value: '" not in r.text, url
        # ...and raw single quotes from the payload never reach the document
        # (every reflection is HTML-entity-encoded inside plain attributes).
        assert "'},alert(document.domain),{x:'" not in r.text, url


def test_f1_static_xdata_kept(client: TestClient) -> None:
    r = client.get("/verify")
    assert r.status_code == 200
    assert 'x-data="{ busy: false }"' in r.text
    r = client.get("/verify/TT-DEMO-0001")
    assert r.status_code == 200
    assert 'value="TT-DEMO-0001"' not in r.text  # detail page has no search echo
    r = client.get("/verify", params={"q": "TT-DEMO-0001"}, follow_redirects=False)
    assert r.status_code == 303  # known serial still redirects to detail


def test_f2_backend_422_renders_error_page_not_500(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx as _httpx

    from app.services import chain_api

    class FakeResp:
        status_code = 422

        def json(self) -> dict:  # pragma: no cover - never reached
            raise AssertionError("must not parse error bodies")

    calls: list[str] = []

    def fake_get(url: str, timeout: float = 15.0) -> FakeResp:
        calls.append(url)
        return FakeResp()

    monkeypatch.setenv("TRUSTTRACE_API_MODE", "chain")
    monkeypatch.setattr(chain_api.httpx, "get", fake_get)
    r = client.get("/verify/SHOW-000001")
    assert r.status_code == 502, r.status_code
    assert "not an all-clear" in r.text
    assert calls, "backend should have been consulted"


def test_f2_backend_429_renders_error_page_not_500(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import chain_api

    class FakeResp:
        status_code = 429

        def json(self) -> dict:  # pragma: no cover - never reached
            raise AssertionError("must not parse error bodies")

    monkeypatch.setenv("TRUSTTRACE_API_MODE", "chain")
    monkeypatch.setattr(chain_api.httpx, "get", lambda url, timeout=15.0: FakeResp())
    r = client.get("/verify/SHOW-000001/bundle")
    assert r.status_code == 502, r.status_code


def test_f2_oversize_serial_rejected_without_backend_call(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services import chain_api

    called = False

    def fake_get(url: str, timeout: float = 15.0):  # pragma: no cover - must not run
        nonlocal called
        called = True
        raise AssertionError("oversize serial must not hit the backend")

    monkeypatch.setenv("TRUSTTRACE_API_MODE", "chain")
    monkeypatch.setattr(chain_api.httpx, "get", fake_get)
    r = client.get("/verify/" + "A" * 5000)
    assert r.status_code == 404, r.status_code
    assert called is False


def test_f4_redirect_encoded_and_filtered(client: TestClient) -> None:
    r = client.post(
        "/red-team/clone-qr/run",
        data={"serial": "A&B", "gap_minutes": "41", "evil\": \"x": "1\r\nX-Injected: yes"},
        follow_redirects=False,
    )
    assert r.status_code == 303, r.status_code
    loc = r.headers["location"]
    assert "\r" not in loc and "\n" not in loc
    qs = parse_qs(urlparse(loc).query)
    assert qs.get("serial") == ["A&B"]
    assert "evil\": \"x" not in loc


def test_f5_form_caps(client: TestClient, clean_mock_lots: object) -> None:
    _ = clean_mock_lots
    big = "R" * 2000
    r = client.post(
        "/lots/LOT-DEMO-B/freeze?as=operator",
        data={"reason": big, "confirm": "LOT-DEMO-B"},
        follow_redirects=False,
    )
    assert r.status_code == 303, r.status_code
    r = client.get(
        "/incidents/INC-1042/actions", params={"action": "note", "note": "N" * 600}
    )
    assert r.status_code in (405, 422), r.status_code  # GET not allowed or note too long
    r = client.post(
        "/incidents/INC-1042/actions", params={"action": "note", "note": "N" * 600},
        follow_redirects=False,
    )
    assert r.status_code == 422, r.status_code

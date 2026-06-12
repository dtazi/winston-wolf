"""send_email error paths (Article 8): Graph refusals must raise loudly —
a send that silently "succeeds" without a 202 is how duplicates are born."""

from __future__ import annotations

import pytest

from ww_outreach import send


class _FakeResponse:
    def __init__(self, status_code: int, text: str = "") -> None:
        self.status_code = status_code
        self.text = text


def _patch_post(monkeypatch, response: _FakeResponse, captured: dict) -> None:
    def fake_post(url, headers=None, json=None, timeout=None):
        captured.update(url=url, headers=headers, json=json, timeout=timeout)
        return response

    monkeypatch.setattr(send.requests, "post", fake_post)


def test_accepted_202_returns_quietly_with_correct_payload(monkeypatch):
    captured: dict = {}
    _patch_post(monkeypatch, _FakeResponse(202), captured)

    send.send_email("tok-123", "buyer@example.com", "Hello", "Body text")

    assert captured["url"] == send.GRAPH_SEND_URL
    assert captured["headers"]["Authorization"] == "Bearer tok-123"
    assert captured["timeout"] == 30  # never hang a send pass on Graph
    msg = captured["json"]["message"]
    assert msg["toRecipients"] == [
        {"emailAddress": {"address": "buyer@example.com"}}
    ]
    assert msg["subject"] == "Hello"
    assert captured["json"]["saveToSentItems"] is True


@pytest.mark.parametrize("status,text", [
    (401, "InvalidAuthenticationToken"),   # expired/revoked token
    (403, "ErrorAccessDenied"),            # scope lost
    (429, "TooManyRequests"),              # throttled
    (500, "InternalServerError"),
])
def test_non_202_raises_with_status_and_body(monkeypatch, status, text):
    _patch_post(monkeypatch, _FakeResponse(status, text), {})

    with pytest.raises(RuntimeError) as exc:
        send.send_email("tok", "buyer@example.com", "S", "B")

    # The operator must see WHAT Graph said, not a generic failure.
    assert str(status) in str(exc.value)
    assert text in str(exc.value)


def test_network_error_propagates_not_swallowed(monkeypatch):
    def boom(*a, **kw):
        raise ConnectionError("dns failure")

    monkeypatch.setattr(send.requests, "post", boom)

    with pytest.raises(ConnectionError):
        send.send_email("tok", "buyer@example.com", "S", "B")

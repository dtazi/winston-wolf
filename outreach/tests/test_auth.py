"""auth error paths (Article 8): a dead/expired session must come back as
None/RuntimeError — never a crash mid-batch, never a silent empty token —
and the token cache must stay private (0600).

msal is faked at the module seam; no network, no real token file touched.
"""

from __future__ import annotations

import stat
from types import SimpleNamespace

import pytest

from ww_outreach import auth


class _FakeCache:
    def __init__(self, state_changed: bool = False) -> None:
        self.has_state_changed = state_changed

    def deserialize(self, text: str) -> None:
        pass

    def serialize(self) -> str:
        return '{"fake": "cache"}'


class _FakeApp:
    """Behavior is injected per-test via class attributes."""

    accounts: list = []
    silent_result: dict | None = None
    flow: dict = {}
    flow_result: dict = {}

    def __init__(self, client_id, authority=None, token_cache=None) -> None:
        pass

    def get_accounts(self):
        return self.accounts

    def acquire_token_silent(self, scopes, account=None):
        return self.silent_result

    def initiate_device_flow(self, scopes):
        return self.flow

    def acquire_token_by_device_flow(self, flow):
        return self.flow_result


@pytest.fixture
def fake_msal(monkeypatch, tmp_path):
    """Route auth at a fake msal + a temp token file; yield the app class."""
    app_cls = type("App", (_FakeApp,), {})  # fresh per test
    monkeypatch.setattr(auth, "msal", SimpleNamespace(
        PublicClientApplication=app_cls,
        SerializableTokenCache=_FakeCache,
    ))
    monkeypatch.setattr(auth, "TOKEN_FILE", tmp_path / "token.json")
    return app_cls


# --- acquire_token_silent: every no-session shape must come back None ------

def test_silent_no_accounts_returns_none(fake_msal):
    fake_msal.accounts = []
    assert auth.acquire_token_silent("cid", "tid") is None


def test_silent_msal_returns_none_returns_none(fake_msal):
    fake_msal.accounts = [{"username": "djaafar@richbond.ma"}]
    fake_msal.silent_result = None  # refresh token expired/revoked
    assert auth.acquire_token_silent("cid", "tid") is None


def test_silent_error_result_without_token_returns_none(fake_msal):
    fake_msal.accounts = [{"username": "djaafar@richbond.ma"}]
    fake_msal.silent_result = {"error": "interaction_required"}
    assert auth.acquire_token_silent("cid", "tid") is None


def test_silent_happy_returns_token(fake_msal):
    fake_msal.accounts = [{"username": "djaafar@richbond.ma"}]
    fake_msal.silent_result = {"access_token": "tok-abc"}
    assert auth.acquire_token_silent("cid", "tid") == "tok-abc"


# --- token cache file hygiene ----------------------------------------------

def test_cache_saved_with_owner_only_permissions(fake_msal, monkeypatch):
    monkeypatch.setattr(
        auth, "_load_cache", lambda: _FakeCache(state_changed=True))
    fake_msal.accounts = [{"username": "djaafar@richbond.ma"}]
    fake_msal.silent_result = {"access_token": "tok"}

    auth.acquire_token_silent("cid", "tid")

    assert auth.TOKEN_FILE.exists()
    mode = stat.S_IMODE(auth.TOKEN_FILE.stat().st_mode)
    assert mode == 0o600  # refresh token must not be group/world readable


def test_unchanged_cache_is_not_written(fake_msal):
    fake_msal.accounts = []
    auth.acquire_token_silent("cid", "tid")
    assert not auth.TOKEN_FILE.exists()


# --- acquire_token_interactive error paths ----------------------------------

def test_interactive_device_flow_start_failure_raises(fake_msal):
    fake_msal.flow = {"error": "invalid_client"}  # no user_code
    with pytest.raises(RuntimeError, match="device flow"):
        auth.acquire_token_interactive("cid", "tid")


def test_interactive_auth_denied_raises_with_reason(fake_msal, capsys):
    fake_msal.flow = {"user_code": "ABC123", "message": "go to ..."}
    fake_msal.flow_result = {
        "error": "access_denied",
        "error_description": "user declined",
    }
    with pytest.raises(RuntimeError, match="user declined"):
        auth.acquire_token_interactive("cid", "tid")


def test_interactive_happy_returns_token(fake_msal, capsys):
    fake_msal.flow = {"user_code": "ABC123", "message": "go to ..."}
    fake_msal.flow_result = {"access_token": "tok-xyz"}
    assert auth.acquire_token_interactive("cid", "tid") == "tok-xyz"


# --- revoke_local ------------------------------------------------------------

def test_revoke_deletes_existing_token(fake_msal):
    auth.TOKEN_FILE.write_text("{}")
    assert auth.revoke_local() is True
    assert not auth.TOKEN_FILE.exists()


def test_revoke_without_token_reports_false(fake_msal):
    assert auth.revoke_local() is False

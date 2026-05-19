"""Microsoft device code OAuth flow + local token storage."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import msal

SCOPES = ["Mail.Send", "Mail.ReadBasic"]
TOKEN_FILE = Path.home() / ".winston-wolf" / "outreach-token.json"


def _load_cache() -> msal.SerializableTokenCache:
    cache = msal.SerializableTokenCache()
    if TOKEN_FILE.exists():
        cache.deserialize(TOKEN_FILE.read_text())
    return cache


def _save_cache(cache: msal.SerializableTokenCache) -> None:
    if not cache.has_state_changed:
        return
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(cache.serialize())
    os.chmod(TOKEN_FILE, stat.S_IRUSR | stat.S_IWUSR)


def _build_app(
    client_id: str, tenant_id: str
) -> tuple[msal.PublicClientApplication, msal.SerializableTokenCache]:
    cache = _load_cache()
    app = msal.PublicClientApplication(
        client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
        token_cache=cache,
    )
    return app, cache


def acquire_token_interactive(client_id: str, tenant_id: str) -> str:
    app, cache = _build_app(client_id, tenant_id)
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        raise RuntimeError(f"Failed to start device flow: {flow}")
    print(flow["message"])
    result = app.acquire_token_by_device_flow(flow)
    _save_cache(cache)
    if "access_token" not in result:
        raise RuntimeError(
            f"Auth failed: {result.get('error_description', result)}"
        )
    return result["access_token"]


def acquire_token_silent(client_id: str, tenant_id: str) -> str | None:
    app, cache = _build_app(client_id, tenant_id)
    accounts = app.get_accounts()
    if not accounts:
        return None
    result = app.acquire_token_silent(SCOPES, account=accounts[0])
    _save_cache(cache)
    if not result or "access_token" not in result:
        return None
    return result["access_token"]


def revoke_local() -> bool:
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
        return True
    return False

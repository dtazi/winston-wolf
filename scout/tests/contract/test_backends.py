"""Adapter seam contract + the keyless NullBackend (T012)."""

from __future__ import annotations

from ww_scout.enrichment.base import (
    EmailBackend,
    NullBackend,
    SearchBackend,
)


def test_null_backend_satisfies_both_protocols():
    nb = NullBackend()
    assert isinstance(nb, SearchBackend)
    assert isinstance(nb, EmailBackend)


def test_null_backend_finds_nothing_without_error():
    nb = NullBackend()
    assert nb.find_domain("Acme", "MT").status == "not_found"
    assert nb.find_person("acme.com", ["procurement"]).status == "not_found"
    assert nb.find_email(first_name="A", last_name="B", domain="acme.com").status == "not_found"


def test_logger_rejects_pii():
    import pytest

    from ww_scout.logging import log_action

    log_action("ok_action", campaign_id="c", count=3)  # fine
    with pytest.raises(ValueError, match="Article 3"):
        log_action("bad", campaign_id="c", person_email="x@y.com")

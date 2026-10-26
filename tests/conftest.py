"""Shared fixtures."""

import pytest


@pytest.fixture(autouse=True)
def _no_retry_sleep(monkeypatch):
    """Throttle-retry backoff must not slow the suite down."""
    monkeypatch.setattr("brand._http.time.sleep", lambda s: None)

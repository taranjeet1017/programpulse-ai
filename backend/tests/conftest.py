"""Offline-by-default tests: never read developer credentials or use real HTTP."""
from pathlib import Path

import httpx
import pytest

from app import config


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    def deny_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("Real HTTP is forbidden in automated tests; use MockTransport")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", deny_network)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", deny_network)

"""Tests for connection/URL handling and the no-token auth path (no network)."""

import pytest

from speckle_mcp.speckle import (
    SpeckleAuthError,
    SpeckleConnection,
    connection_from_env,
    normalize_host,
)


def test_normalize_host_strips_https():
    assert normalize_host("https://app.speckle.systems") == ("app.speckle.systems", True)


def test_normalize_host_http_sets_use_ssl_false():
    assert normalize_host("http://localhost:3000") == ("localhost:3000", False)


def test_normalize_host_bare_and_trailing_slash():
    assert normalize_host("speckle.example.com/") == ("speckle.example.com", True)


def test_server_label_roundtrips():
    conn = SpeckleConnection(token="x", server_url="http://localhost:3000/")
    assert conn.server_label == "http://localhost:3000"
    assert conn.has_token is True


def test_authenticated_client_without_token_raises_before_network():
    conn = SpeckleConnection(token=None, server_url="https://app.speckle.systems")
    assert conn.has_token is False
    with pytest.raises(SpeckleAuthError):
        conn.authenticated_client()


def test_connection_from_env_defaults_to_public_server(monkeypatch):
    monkeypatch.delenv("SPECKLE_TOKEN", raising=False)
    monkeypatch.delenv("SPECKLE_SERVER_URL", raising=False)
    conn = connection_from_env()
    assert conn.server_label == "https://app.speckle.systems"
    assert conn.has_token is False

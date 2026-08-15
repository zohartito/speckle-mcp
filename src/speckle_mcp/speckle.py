"""Speckle connection and authentication for the MCP server.

Wraps specklepy's ``SpeckleClient`` with lazy, cached authentication driven by
environment variables (``SPECKLE_TOKEN``, ``SPECKLE_SERVER_URL``). Public
endpoints (server info) work without a token; every other tool requires one.
"""

from __future__ import annotations

import os

from specklepy.api.client import SpeckleClient

DEFAULT_SERVER_URL = "https://app.speckle.systems"


class SpeckleAuthError(RuntimeError):
    """Raised when a tool needs a token that is missing, invalid, or expired."""


def normalize_host(server_url: str) -> tuple[str, bool]:
    """Split a server URL into ``(bare_host, use_ssl)``.

    ``SpeckleClient`` wants a bare host (no scheme) plus a ``use_ssl`` flag.
    Accepts values with or without a scheme and tolerates a trailing slash.
    """
    url = server_url.strip().rstrip("/")
    use_ssl = True
    if url.startswith("http://"):
        use_ssl = False
        url = url[len("http://"):]
    elif url.startswith("https://"):
        url = url[len("https://"):]
    return url, use_ssl


class SpeckleConnection:
    """Lazily builds and caches an (optionally authenticated) ``SpeckleClient``."""

    def __init__(self, token: str | None, server_url: str) -> None:
        self._token = token or None
        self._host, self._use_ssl = normalize_host(server_url)
        self._authed_client: SpeckleClient | None = None

    @property
    def has_token(self) -> bool:
        return self._token is not None

    @property
    def server_label(self) -> str:
        scheme = "https" if self._use_ssl else "http"
        return f"{scheme}://{self._host}"

    def anonymous_client(self) -> SpeckleClient:
        """A client with no auth — valid only for public endpoints (server info)."""
        return SpeckleClient(host=self._host, use_ssl=self._use_ssl)

    def authenticated_client(self) -> SpeckleClient:
        """A cached, token-authenticated client.

        Raises ``SpeckleAuthError`` if no token is configured or the server
        rejects it.
        """
        if self._authed_client is not None:
            return self._authed_client

        if not self._token:
            raise SpeckleAuthError(
                "No Speckle token configured. Set the SPECKLE_TOKEN environment "
                "variable to a personal access token from "
                f"{self.server_label}/profile"
            )

        client = SpeckleClient(host=self._host, use_ssl=self._use_ssl)
        client.authenticate_with_token(self._token)

        # authenticate_with_token does not raise on a bad token; a null active
        # user is how a rejected token surfaces.
        if client.active_user.get() is None:
            raise SpeckleAuthError(
                f"Speckle server {self.server_label} rejected the token. It may be "
                "invalid, expired, or issued for a different server."
            )

        self._authed_client = client
        return client


def connection_from_env() -> SpeckleConnection:
    """Build a :class:`SpeckleConnection` from environment variables."""
    token = os.environ.get("SPECKLE_TOKEN")
    server_url = os.environ.get("SPECKLE_SERVER_URL", DEFAULT_SERVER_URL)
    return SpeckleConnection(token=token, server_url=server_url)

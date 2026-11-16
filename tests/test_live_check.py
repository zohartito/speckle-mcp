"""Live-check control flow with synthetic clients only; no network or accounts."""

import importlib.util
from pathlib import Path
from speckle_mcp import server

spec = importlib.util.spec_from_file_location(
    "live_check", Path(__file__).resolve().parents[1] / "scripts/live_check.py"
)
live_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(live_check)


def test_live_check_offline_is_failure(monkeypatch, capsys):
    monkeypatch.delenv("SPECKLE_TOKEN", raising=False)

    def offline():
        raise RuntimeError("synthetic offline")

    monkeypatch.setattr(server._conn, "anonymous_client", offline)
    assert live_check.main() == 1
    assert "synthetic offline" in capsys.readouterr().out


def test_live_check_auth_failure_is_failure(monkeypatch, capsys):
    monkeypatch.setenv("SPECKLE_TOKEN", "synthetic-test-value")
    monkeypatch.setattr(server, "speckle_server_info", lambda: "server info")
    monkeypatch.setattr(server._conn, "_token", None)
    monkeypatch.setattr(server._conn, "_authed_client", None)
    assert live_check.main() == 1
    assert "Authentication error:" in capsys.readouterr().out


def test_live_check_anonymous_success(monkeypatch, capsys):
    monkeypatch.delenv("SPECKLE_TOKEN", raising=False)
    monkeypatch.setattr(server, "speckle_server_info", lambda: "server info")
    assert live_check.main() == 0
    assert "skipping authenticated checks" in capsys.readouterr().out

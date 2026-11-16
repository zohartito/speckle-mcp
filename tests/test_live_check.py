"""Live-check control flow with synthetic clients only; no network or accounts."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest
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


TOOLS = (
    "speckle_server_info", "speckle_whoami", "speckle_list_projects",
    "speckle_project_details", "speckle_list_models", "speckle_model_versions",
    "speckle_object_data",
)


def _stub_tools(monkeypatch):
    calls = []
    for name in TOOLS:
        def call(*args, _name=name, **kwargs):
            calls.append((_name, args, kwargs))
            return "synthetic result"
        monkeypatch.setattr(server, name, call)
    return calls


def test_live_check_paginates_projects_and_models(monkeypatch, capsys):
    monkeypatch.setenv("SPECKLE_TOKEN", "synthetic-test-value")
    calls = _stub_tools(monkeypatch)
    project_cursors = []
    model_cursors = []

    def projects(*, limit, filter, cursor=None):
        assert limit == 5 and filter.include_implicit_access
        project_cursors.append(cursor)
        ids = range(5) if cursor is None else [5]
        return SimpleNamespace(items=[SimpleNamespace(id=f"p{i}") for i in ids],
                               cursor="next-projects" if cursor is None else None)

    def models(project_id, *, models_limit, models_cursor=None):
        assert models_limit == 5
        model_cursors.append((project_id, models_cursor))
        ids = range(5) if models_cursor is None else [5]
        return SimpleNamespace(items=[SimpleNamespace(id=f"m{i}") for i in ids],
                               cursor="next-models" if project_id == "p5" and models_cursor is None else None)

    def versions(model_id, project_id, *, versions_limit):
        assert versions_limit == 1
        items = [SimpleNamespace(id="v1")] if (project_id, model_id) == ("p5", "m5") else []
        return SimpleNamespace(versions=SimpleNamespace(items=items))

    client = SimpleNamespace(active_user=SimpleNamespace(get_projects=projects),
                             model=SimpleNamespace(get_models=models, get_with_versions=versions))
    monkeypatch.setattr(server._conn, "authenticated_client", lambda: client)
    assert live_check.main() == 0
    assert [name for name, _, _ in calls] == list(TOOLS)
    assert project_cursors == [None, "next-projects"]
    assert ("p5", "next-models") in model_cursors
    assert calls[-1] == ("speckle_object_data", ("p5", "v1"), {"max_depth": 1, "max_children": 5})
    output = capsys.readouterr().out
    assert "Exercised: " + ", ".join(TOOLS) in output
    assert "Skipped: none" in output


@pytest.mark.parametrize("has_token", [False, True])
def test_live_check_names_skipped_tools(monkeypatch, capsys, has_token):
    calls = _stub_tools(monkeypatch)
    if has_token:
        monkeypatch.setenv("SPECKLE_TOKEN", "synthetic-test-value")
    else:
        monkeypatch.delenv("SPECKLE_TOKEN", raising=False)
    empty = SimpleNamespace(items=[], cursor=None)
    client = SimpleNamespace(active_user=SimpleNamespace(get_projects=lambda **kwargs: empty))
    monkeypatch.setattr(server._conn, "authenticated_client", lambda: client)
    assert live_check.main() == 0
    count = 3 if has_token else 1
    assert [name for name, _, _ in calls] == list(TOOLS[:count])
    assert "Skipped: " + ", ".join(TOOLS[count:]) in capsys.readouterr().out

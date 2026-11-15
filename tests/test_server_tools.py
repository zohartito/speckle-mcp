"""Tool behaviour found wrong by the first live run against app.speckle.systems (no network)."""

from types import SimpleNamespace

import specklepy.logging.metrics as metrics

from speckle_mcp import server


class _FakeActiveUser:
    def __init__(self):
        self.calls = []

    def get_projects(self, limit, filter):
        self.calls.append((limit, filter))
        return SimpleNamespace(items=[], total_count=0)


def _fake_client(monkeypatch):
    active_user = _FakeActiveUser()
    monkeypatch.setattr(
        server._conn, "authenticated_client", lambda: SimpleNamespace(active_user=active_user)
    )
    return active_user


def test_list_projects_includes_workspace_projects(monkeypatch):
    # A project reached through workspace membership is "implicit access". Without the
    # flag the live server returned zero projects for a workspace that had one.
    active_user = _fake_client(monkeypatch)
    server.speckle_list_projects()
    ((limit, projects_filter),) = active_user.calls
    assert limit == 25
    assert projects_filter.include_implicit_access is True
    assert projects_filter.search is None


def test_list_projects_search_still_includes_workspace_projects(monkeypatch):
    active_user = _fake_client(monkeypatch)
    server.speckle_list_projects(search="tower", limit=5)
    ((limit, projects_filter),) = active_user.calls
    assert limit == 5
    assert projects_filter.search == "tower"
    assert projects_filter.include_implicit_access is True


def test_usage_tracking_is_off():
    # specklepy reports usage to Speckle's analytics host unless told not to.
    assert metrics.TRACK is False

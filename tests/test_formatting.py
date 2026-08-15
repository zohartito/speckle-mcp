"""Tests for the pure Markdown formatters and Base serialization.

Uses ``SimpleNamespace`` stand-ins that mirror the live SDK's snake_case fields,
plus a real specklepy ``Base`` for ``base_to_dict``. No network involved.
"""

from types import SimpleNamespace

from specklepy.objects.base import Base

from speckle_mcp import formatting


def _collection(items, total=None):
    return SimpleNamespace(items=items, total_count=total if total is not None else len(items))


def test_fmt_dt_trims_and_handles_missing():
    assert formatting._fmt_dt("2026-08-15T12:34:56.789Z") == "2026-08-15 12:34:56"
    assert formatting._fmt_dt(None) == "N/A"


def test_md_table_escapes_pipes_and_handles_empty():
    assert formatting._md_table([], ["a"]) == "_(none)_"
    table = formatting._md_table([{"a": "x|y"}], ["a"])
    assert "x\\|y" in table


def test_format_server_info_reads_snake_case():
    info = SimpleNamespace(name="Speckle", version="2026.6.1", company="AEC Systems", description="hub")
    out = formatting.format_server_info(info, "https://app.speckle.systems")
    assert "Speckle" in out and "2026.6.1" in out and "AEC Systems" in out


def test_format_projects_uses_updated_at_not_camelcase():
    # Regression guard: the live field is updated_at (snake_case), not updatedAt.
    projects = [SimpleNamespace(name="Hospital", id="abc123", role="stream:owner",
                                visibility="private", updated_at="2026-08-01T09:00:00Z")]
    out = formatting.format_projects(projects, 1, "https://app.speckle.systems")
    assert "Hospital" in out
    assert "abc123" in out
    assert "2026-08-01 09:00:00" in out  # would be N/A if we read the wrong field
    assert "owner" in out  # "stream:" prefix stripped


def test_format_projects_empty_and_search():
    assert "No projects" in formatting.format_projects([], 0, "https://s")
    assert "matching 'foo'" in formatting.format_projects([], 0, "https://s", search="foo")


def test_format_model_versions_reads_author_user_snake_case():
    version = SimpleNamespace(
        id="v1", message="initial send", source_application="Rhino",
        created_at="2026-08-10T10:00:00Z", referenced_object="obj-xyz",
        author_user=SimpleNamespace(name="Zohar"),
    )
    model = SimpleNamespace(name="Structure", id="m1", description="",
                            versions=_collection([version]))
    out = formatting.format_model_versions(model, "p1")
    assert "Zohar" in out          # would be "Unknown" if we read authorUser
    assert "Rhino" in out
    assert "initial send" in out
    assert "obj-xyz" in out


def test_format_project_details_lists_models():
    model = SimpleNamespace(name="Arch", id="m1", updated_at="2026-08-02T00:00:00Z")
    project = SimpleNamespace(id="p1", name="School", description="d", visibility="private",
                              role="stream:owner", created_at="2026-07-01T00:00:00Z",
                              updated_at="2026-08-02T00:00:00Z", models=_collection([model]))
    out = formatting.format_project_details(project, "https://app.speckle.systems")
    assert "School" in out
    assert "Arch" in out
    assert "https://app.speckle.systems/projects/p1" in out


def test_base_to_dict_expands_and_caps():
    root = Base()
    root.name = "Wall"
    child = Base()
    child.height = 3.0
    root.child = child
    root.points = list(range(100))

    data = formatting.base_to_dict(root, max_depth=2, max_children=5)
    assert data["name"] == "Wall"
    assert isinstance(data["child"], dict)
    assert data["child"]["height"] == 3.0
    # 100-item list capped to 5 entries + one truncation marker
    assert len(data["points"]) == 6
    assert "more of 100" in data["points"][-1]


def test_base_to_dict_truncates_beyond_max_depth():
    root = Base()
    child = Base()
    child.value = 1
    root.child = child

    data = formatting.base_to_dict(root, max_depth=0)
    assert data["child"]["_truncated"] == "max depth reached"


def test_format_object_data_wraps_json_and_caps_size():
    version = SimpleNamespace(id="v1", referenced_object="obj1", source_application="Rhino")
    small = formatting.format_object_data(version, {"a": 1}, "p1", 2, 25)
    assert "```json" in small and '"a": 1' in small

    big = formatting.format_object_data(version, {"blob": "x" * 20000}, "p1", 2, 25)
    assert "truncated" in big

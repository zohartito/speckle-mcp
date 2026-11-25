#!/usr/bin/env python3
"""Live end-to-end check against a real Speckle server.

- Always runs the unauthenticated ``server_info`` round-trip (no token needed).
- If ``SPECKLE_TOKEN`` is set, also exercises the authenticated read tools:
  whoami, list projects, and (if a project/model/version exists) project details,
  models, versions and object data.

Run: ``python scripts/live_check.py``
"""

from __future__ import annotations

import os
import sys

# Import the tool functions directly — they return ready-to-print Markdown.
from speckle_mcp import server

_TOOLS = (
    "speckle_server_info", "speckle_whoami", "speckle_list_projects",
    "speckle_project_details", "speckle_list_models", "speckle_model_versions",
    "speckle_object_data",
)


def _section(title: str) -> None:
    print(f"\n{'=' * 4} {title} {'=' * 4}")


def main() -> int:
    exercised: list[str] = []
    try:
        return _run(exercised)
    except Exception as exc:
        print(f"Live check failed: {exc}")
        return 1
    finally:
        print("\nExercised: " + (", ".join(exercised) or "none"))
        print("Skipped: " + (", ".join(name for name in _TOOLS if name not in exercised) or "none"))


def _check(exercised: list[str], name: str, *args, **kwargs) -> None:
    _section(name)
    exercised.append(name)
    print(getattr(server, name)(*args, **kwargs))


def _items(fetch_page):
    cursor = None
    seen = set()
    while True:
        page = fetch_page(cursor)
        yield from page.items
        cursor = page.cursor
        if not cursor:
            return
        if cursor in seen:
            raise RuntimeError("Discovery returned a repeated pagination cursor")
        seen.add(cursor)


def _run(exercised: list[str]) -> int:
    _check(exercised, "speckle_server_info")

    if not os.environ.get("SPECKLE_TOKEN"):
        _section("authenticated tools")
        print("SPECKLE_TOKEN not set — skipping authenticated checks.")
        print("Set it and re-run to exercise the full read surface.")
        return 0

    _check(exercised, "speckle_whoami")
    _check(exercised, "speckle_list_projects", limit=5)

    # Drill down into the first project that has a model with a version, so every
    # tool runs against real data: details, models, versions, object data.
    client = server._conn.authenticated_client()
    projects = _items(lambda cursor: client.active_user.get_projects(
        limit=5, cursor=cursor, filter=server.UserProjectsFilter(include_implicit_access=True)
    ))
    for project in projects:
        models = _items(lambda cursor: client.model.get_models(
            project.id, models_limit=5, models_cursor=cursor
        ))
        for model in models:
            versions = client.model.get_with_versions(model.id, project.id, versions_limit=1).versions.items
            if not versions:
                continue
            _check(exercised, "speckle_project_details", project.id)
            _check(exercised, "speckle_list_models", project.id)
            _check(exercised, "speckle_model_versions", project.id, model.id)
            _check(exercised, "speckle_object_data", project.id, versions[0].id, max_depth=1, max_children=5)
            return 0
    print("\nNo project with a published version was found; the drill-down tools were not exercised.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

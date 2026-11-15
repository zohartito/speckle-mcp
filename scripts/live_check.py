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


def _section(title: str) -> None:
    print(f"\n{'=' * 4} {title} {'=' * 4}")


def main() -> int:
    _section("speckle_server_info (no auth)")
    print(server.speckle_server_info())

    if not os.environ.get("SPECKLE_TOKEN"):
        _section("authenticated tools")
        print("SPECKLE_TOKEN not set — skipping authenticated checks.")
        print("Set it and re-run to exercise the full read surface.")
        return 0

    _section("speckle_whoami")
    print(server.speckle_whoami())

    _section("speckle_list_projects (limit 5)")
    print(server.speckle_list_projects(limit=5))

    # Drill down into the first project that has a model with a version, so every
    # tool runs against real data: details, models, versions, object data.
    client = server._conn.authenticated_client()
    projects = client.active_user.get_projects(
        limit=5, filter=server.UserProjectsFilter(include_implicit_access=True)
    ).items
    for project in projects:
        models = client.model.get_models(project.id, models_limit=5).items
        for model in models:
            versions = client.model.get_with_versions(model.id, project.id, versions_limit=1).versions.items
            if not versions:
                continue
            _section(f"speckle_project_details ({project.id})")
            print(server.speckle_project_details(project.id))
            _section("speckle_list_models")
            print(server.speckle_list_models(project.id))
            _section(f"speckle_model_versions ({model.id})")
            print(server.speckle_model_versions(project.id, model.id))
            _section(f"speckle_object_data ({versions[0].id}, depth 1)")
            print(server.speckle_object_data(project.id, versions[0].id, max_depth=1, max_children=5))
            return 0
    print("\nNo project with a published version was found; the drill-down tools were not exercised.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

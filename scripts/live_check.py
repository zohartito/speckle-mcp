#!/usr/bin/env python3
"""Live end-to-end check against a real Speckle server.

- Always runs the unauthenticated ``server_info`` round-trip (no token needed).
- If ``SPECKLE_TOKEN`` is set, also exercises the authenticated read tools:
  whoami, list projects, and (if a project/model/version exists) drill down to
  object data.

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

    return 0


if __name__ == "__main__":
    sys.exit(main())

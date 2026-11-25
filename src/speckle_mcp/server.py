"""Speckle MCP server — read-only access to Speckle over the Model Context Protocol.

Exposes projects, models, versions, and the object data behind a version as MCP
tools. Speckle is the AEC interoperability hub that federates Rhino, Revit,
Grasshopper, Blender, QGIS, and Excel data into one graph; this server lets an
agent read that graph.

Run with ``speckle-mcp`` (or ``python -m speckle_mcp.server``). Configuration is
via environment variables: ``SPECKLE_TOKEN`` (required for every tool except
``speckle_server_info``) and ``SPECKLE_SERVER_URL`` (optional, defaults to
https://app.speckle.systems).
"""

from __future__ import annotations

import asyncio
import functools
import sys
from typing import Callable, TypeVar

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from specklepy.api import operations
from specklepy.api.inputs.user_inputs import UserProjectsFilter
from specklepy.logging import metrics
from specklepy.transports.server import ServerTransport

from . import formatting
from .speckle import SpeckleAuthError, connection_from_env

server = MCPServer(
    name="speckle-mcp",
    version="0.1.0",
    instructions=(
        "Read-only access to Speckle, the AEC data hub. List and inspect "
        "projects, models, and versions, and fetch the object data behind a "
        "version. Every tool except speckle_server_info needs a SPECKLE_TOKEN "
        "personal access token."
    ),
)

# specklepy reports usage to Speckle's analytics host by default. A read-only tool an
# agent calls should not phone home on the user's behalf.
metrics.disable()

_conn = connection_from_env()

_F = TypeVar("_F", bound=Callable[..., str])


def safe_tool(fn: _F) -> _F:
    """Turn any exception raised by a tool into a readable MCP tool error.

    The SDK reports ToolError as is_error=True without crashing the server.
    Authentication problems retain a clearer note than a raw traceback.
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except SpeckleAuthError as exc:
            raise ToolError(f"Authentication error: {formatting.sanitize_text(exc)}") from exc
        except Exception as exc:  # surfaced to the caller as tool output
            raise ToolError(f"Error: {formatting.sanitize_text(exc)}") from exc

    return wrapper  # type: ignore[return-value]


@server.tool(
    description=(
        "Get public information about the configured Speckle server (name, "
        "version, company). Works without a token — a quick connectivity check."
    )
)
@safe_tool
def speckle_server_info() -> str:
    client = _conn.anonymous_client()
    info = client.server.get()
    return formatting.format_server_info(info, _conn.server_label)


@server.tool(
    description=(
        "Show which user the configured SPECKLE_TOKEN authenticates as. "
        "Confirms the token is valid."
    )
)
@safe_tool
def speckle_whoami() -> str:
    client = _conn.authenticated_client()
    user = client.active_user.get()
    return formatting.format_user(user, _conn.server_label)


@server.tool(
    description=(
        "List Speckle projects accessible to the authenticated user. Optionally "
        "filter by a search term that matches project names."
    )
)
@safe_tool
def speckle_list_projects(search: str = "", limit: int = 25) -> str:
    client = _conn.authenticated_client()
    # include_implicit_access: projects reached through workspace membership. Without
    # it the server lists only projects the user was added to one by one.
    projects_filter = UserProjectsFilter(search=search or None, include_implicit_access=True)
    result = client.active_user.get_projects(limit=limit, filter=projects_filter)
    return formatting.format_projects(
        result.items, result.total_count, _conn.server_label, search
    )


@server.tool(
    description="Get details for one Speckle project, including the models it contains."
)
@safe_tool
def speckle_project_details(project_id: str) -> str:
    client = _conn.authenticated_client()
    project = client.project.get_with_models(project_id)
    return formatting.format_project_details(project, _conn.server_label)


@server.tool(description="List the models inside a Speckle project.")
@safe_tool
def speckle_list_models(project_id: str, limit: int = 25) -> str:
    client = _conn.authenticated_client()
    project = client.project.get(project_id)
    result = client.model.get_models(project_id, models_limit=limit)
    return formatting.format_models(
        result.items, result.total_count, project_id, project.name
    )


@server.tool(
    description=(
        "Get a model's version history (who sent what, when, and from which "
        "application) within a project."
    )
)
@safe_tool
def speckle_model_versions(project_id: str, model_id: str, limit: int = 25) -> str:
    client = _conn.authenticated_client()
    model = client.model.get_with_versions(model_id, project_id, versions_limit=limit)
    return formatting.format_model_versions(model, project_id)


@server.tool(
    description=(
        "Fetch the actual object data (properties and nested geometry tree) "
        "behind a specific version. Depth and children per collection are capped "
        "to keep output readable."
    )
)
@safe_tool
def speckle_object_data(
    project_id: str,
    version_id: str,
    max_depth: int = 2,
    max_children: int = 25,
) -> str:
    client = _conn.authenticated_client()
    version = client.version.get(version_id, project_id)
    transport = ServerTransport(stream_id=project_id, client=client)
    root = operations.receive(version.referenced_object, remote_transport=transport)
    data = formatting.base_to_dict(root, max_depth=max_depth, max_children=max_children)
    return formatting.format_object_data(version, data, project_id, max_depth, max_children)


def main() -> None:
    """Entry point: start the server on stdio transport."""
    print("speckle-mcp starting (read-only Speckle MCP server)...", file=sys.stderr)
    print(f"  server: {_conn.server_label}", file=sys.stderr)
    if _conn.has_token:
        token_state = "set"
    else:
        token_state = "NOT set — only speckle_server_info will work"
    print(f"  SPECKLE_TOKEN: {token_state}", file=sys.stderr)
    asyncio.run(server.run_stdio_async())


if __name__ == "__main__":
    main()

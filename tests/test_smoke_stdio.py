"""End-to-end smoke test: launch the server over stdio and read its tool list.

This proves the MCP wiring works — the server starts, speaks the protocol, and
advertises every tool, and preserves the object-data input schema without a token.
"""

import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

EXPECTED_TOOLS = {
    "speckle_server_info",
    "speckle_whoami",
    "speckle_list_projects",
    "speckle_project_details",
    "speckle_list_models",
    "speckle_model_versions",
    "speckle_object_data",
}


async def _list_tools() -> dict:
    env = dict(os.environ)
    env.pop("SPECKLE_TOKEN", None)  # tools must be listable with no token
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "speckle_mcp.server"],
        env=env,
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            return {tool.name: tool for tool in result.tools}


def test_all_tools_advertised_over_stdio():
    tools = asyncio.run(_list_tools())
    missing = EXPECTED_TOOLS - set(tools)
    assert not missing, f"missing tools: {missing}"


def test_schema_survives_the_error_wrapper():
    # If functools.wraps did not preserve the signature through safe_tool, the
    # inferred schema would lose these parameters. This guards that.
    tools = asyncio.run(_list_tools())
    schema = tools["speckle_object_data"].input_schema
    props = set(schema.get("properties", {}))
    assert {"project_id", "version_id", "max_depth", "max_children"} <= props
    assert set(schema.get("required", [])) >= {"project_id", "version_id"}


async def _call_without_token():
    env = dict(os.environ)
    env.pop("SPECKLE_TOKEN", None)
    params = StdioServerParameters(command=sys.executable, args=["-m", "speckle_mcp.server"], env=env)
    calls = {
        "speckle_whoami": {},
        "speckle_list_projects": {},
        "speckle_project_details": {"project_id": "p1"},
        "speckle_list_models": {"project_id": "p1"},
        "speckle_model_versions": {"project_id": "p1", "model_id": "m1"},
        "speckle_object_data": {"project_id": "p1", "version_id": "v1"},
    }
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return {name: await session.call_tool(name, args) for name, args in calls.items()}


def test_missing_token_calls_are_mcp_errors():
    results = asyncio.run(_call_without_token())
    assert len(results) == 6
    assert all(result.is_error for result in results.values()), {
        name: result.is_error for name, result in results.items()
    }
    for result in results.values():
        assert "Authentication error: No Speckle token configured" in result.content[0].text

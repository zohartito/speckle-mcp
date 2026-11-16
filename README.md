# speckle-mcp

A read-only [Model Context Protocol](https://modelcontextprotocol.io/) server for
[Speckle](https://speckle.systems/) — the open-source AEC interoperability hub that
federates Rhino, Revit, Grasshopper, Blender, QGIS, and Excel data into one graph.

This server lets an MCP client (Claude Code, Claude Desktop, etc.) **read** that
graph in plain language: list projects, inspect models, walk version history, and
pull the actual object data behind a version.

It talks to Speckle's current **Next Gen (v3) GraphQL API** through the official
[`specklepy`](https://github.com/specklesystems/specklepy) SDK, so it works against
`app.speckle.systems` or any self-hosted Speckle server.

---

## Tools

| Tool | What it does | Needs token |
|------|--------------|:-----------:|
| `speckle_server_info` | Public server info (name, version, company). Doubles as a connectivity check. | No |
| `speckle_whoami` | Show which user your token authenticates as. | Yes |
| `speckle_list_projects` | List accessible projects; optional `search` term filters by name. | Yes |
| `speckle_project_details` | One project's details plus the models it contains. | Yes |
| `speckle_list_models` | List the models inside a project. | Yes |
| `speckle_model_versions` | A model's version history — who sent what, when, from which app. | Yes |
| `speckle_object_data` | The actual object tree behind a version (properties + geometry), depth/size capped. | Yes |

`speckle_object_data` is the differentiator: it uses `operations.receive()` to pull
the real committed data so an agent can reason about the BIM/CAD content, not just
metadata. Output is capped by `max_depth` (default 2) and `max_children` (default 25)
per collection so a heavy model stays readable.

## What this does NOT do (v0.1 scope)

This release is **read-only, on purpose**. Out of scope for v0.1:

- **Writing / sending geometry.** Pushing objects into Speckle is a much larger
  surface (object serialization, chunking, transports, commit creation) and is best
  done by the native Speckle connectors (Revit, Rhino, Grasshopper, Blender, …),
  which are already first-class. An MCP "send" tool would either duplicate them
  poorly or just print instructions.
- **Creating projects/models, managing teams, invites, permissions.** Mutations are
  deferred until the read surface is proven useful.
- **Speckle Automate, webhooks, subscriptions.**

Reading is where an AI agent adds the most value today, and it is the part that can
be built and tested without any desktop application open.

## Requirements

- Python 3.11+
- A Speckle account and a **personal access token** (see below)

## Configuration

Authentication is via environment variables. **You must create the token yourself —
it is never hardcoded or committed.**

1. Create a personal access token under **Settings → Developer → Access tokens** on
   your Speckle server. Read-only scopes are enough. The live run recorded below used
   three: Projects → Core → Read (`project.core.read`), Workspaces → Core → Read and
   Account → Profile → Read. A smaller set was not tried.
2. Provide it via the environment:

   ```bash
   export SPECKLE_TOKEN="your-personal-access-token"
   # optional, for self-hosted servers (defaults to https://app.speckle.systems):
   export SPECKLE_SERVER_URL="https://your.speckle.server"
   ```

   `.env.example` lists the supported variables for reference. .env files are not loaded
   by the server; export the values as above or configure your MCP client's environment.

## Install & register with Claude Code

Once published or from the local checkout, register it with:

```bash
claude mcp add speckle \
  --env SPECKLE_TOKEN=your-personal-access-token \
  -- uvx --from /path/to/speckle-mcp speckle-mcp
```

(Replace the path with the install location. `--env SPECKLE_SERVER_URL=...` too if
self-hosting.) `speckle_server_info` works even without a token, so you can confirm
the server is wired up before pasting a token in.

For **Claude Desktop**, add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "speckle": {
      "command": "uvx",
      "args": ["--from", "/path/to/speckle-mcp", "speckle-mcp"],
      "env": { "SPECKLE_TOKEN": "your-personal-access-token" }
    }
  }
}
```

## Development

```bash
uv venv --python 3.11 .venv
source .venv/bin/activate
uv pip install -e ".[dev]"
python -m pytest -v
```

### Test coverage

- **Unit tests** (`test_speckle.py`, `test_formatting.py`) cover URL normalization,
  the no-token auth path, Markdown formatting against the live snake_case SDK
  fields, and `Base` object serialization (depth/children caps). No network needed.
- **Smoke test** (`test_smoke_stdio.py`) launches the server over stdio with the
  official MCP client, calls `tools/list`, and asserts all seven tools are
  advertised with correct input schemas — proving the MCP wiring works without a
  token.
- **Tool tests** (`test_server_tools.py`) cover the two behaviours the first live run
  found wrong (see below) and check that usage tracking is off. No network needed.
- **Live check** (`scripts/live_check.py`) hits the public `server.get()` endpoint
  (no auth) end to end. With `SPECKLE_TOKEN` set it paginates projects and models
  to find the first published version and exercise all seven tools. It lists
  exercised/skipped tools, including when no version is found, and exits nonzero
  on a failed check.

### Live run, 2026-11-15

All seven tools were run against app.speckle.systems (server 2026.11.0) with a
read-only token, on the sample project a new workspace's sandbox comes with (one
Rhino model, one Revit model). That is one server, one account and sample data, not
a range of real projects.

The first run found two failures, both fixed in this version:

- `speckle_list_projects` returned nothing for a project reached through workspace
  membership. It now asks for projects with implicit access too.
- `speckle_object_data` failed with `BUNDLE_REFERENCE_NOT_FOUND`. Current Speckle
  servers store a version as a `bundle.*` reference, which specklepy reads from
  2026.9 on with its `bundle` extra (pyarrow). The dependency is now
  `specklepy[bundle]>=2026.9.2`.

### Usage tracking

specklepy reports usage to Speckle's analytics host by default. This server turns
that off at start-up (`metrics.disable()`).

## License

MIT

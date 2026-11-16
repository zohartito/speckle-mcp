"""Pure formatting helpers: turn Speckle SDK objects into readable Markdown.

Everything here is side-effect free and network-free, so it can be unit tested
with lightweight stand-in objects. Attribute access is defensive (``getattr``
with defaults) because the live SDK models use snake_case fields and occasional
nulls.
"""

from __future__ import annotations

import json
from typing import Any

# Cap for the JSON blob emitted by ``format_object_data`` so a large model does
# not flood the conversation. Depth/children caps happen earlier in base_to_dict.
_OBJECT_JSON_CHAR_LIMIT = 12000


def _fmt_dt(value: Any) -> str:
    """Trim an ISO-ish datetime to ``YYYY-MM-DD HH:MM:SS``; ``N/A`` when missing."""
    if not value:
        return "N/A"
    return str(value)[:19].replace("T", " ")


def _clean(value: Any) -> str:
    """Return a stripped string, or ``N/A`` for empty/None values."""
    text = (str(value).strip() if value is not None else "")
    return text or "N/A"


def _md_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    """Render a list of dicts as a GitHub-flavoured Markdown table."""
    if not rows:
        return "_(none)_"
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, divider]
    for row in rows:
        cells = [str(row.get(col, "")).replace("|", "\\|") for col in columns]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def format_server_info(info: Any, server_label: str) -> str:
    return (
        f"# Speckle server: {getattr(info, 'name', 'Unknown')}\n\n"
        f"- **URL:** {server_label}\n"
        f"- **Version:** {_clean(getattr(info, 'version', None))}\n"
        f"- **Company:** {_clean(getattr(info, 'company', None))}\n"
        f"- **Description:** {_clean(getattr(info, 'description', None))}\n"
    )


def format_user(user: Any, server_label: str) -> str:
    return (
        f"# Authenticated as {getattr(user, 'name', 'Unknown')}\n\n"
        f"- **ID:** `{getattr(user, 'id', 'N/A')}`\n"
        f"- **Email:** {_clean(getattr(user, 'email', None))}\n"
        f"- **Company:** {_clean(getattr(user, 'company', None))}\n"
        f"- **Role:** {_clean(getattr(user, 'role', None))}\n"
        f"- **Server:** {server_label}\n"
    )


def format_projects(items: list, total: int, server_label: str, search: str = "") -> str:
    if not items:
        target = f" matching '{search}'" if search else ""
        return f"No projects{target} found on {server_label}."
    rows = []
    for project in items:
        rows.append({
            "name": getattr(project, "name", "Unnamed"),
            "id": getattr(project, "id", "?"),
            "role": (getattr(project, "role", "") or "").replace("stream:", ""),
            "visibility": getattr(project, "visibility", "") or "",
            "updated": _fmt_dt(getattr(project, "updated_at", None)),
        })
    table = _md_table(rows, ["name", "id", "role", "visibility", "updated"])
    heading = f"Projects matching '{search}'" if search else "Projects"
    return f"## {heading} ({total} total on {server_label})\n\n{table}"


def format_project_details(project: Any, server_label: str) -> str:
    project_id = getattr(project, "id", "?")
    lines = [
        f"# Project: {getattr(project, 'name', 'Unnamed')}",
        "",
        f"- **ID:** `{project_id}`",
        f"- **Description:** {_clean(getattr(project, 'description', None))}",
        f"- **Visibility:** {_clean(getattr(project, 'visibility', None))}",
        f"- **Role:** {_clean(getattr(project, 'role', None))}",
        f"- **Created:** {_fmt_dt(getattr(project, 'created_at', None))}",
        f"- **Updated:** {_fmt_dt(getattr(project, 'updated_at', None))}",
        f"- **URL:** {server_label}/projects/{project_id}",
        "",
    ]
    models = getattr(project, "models", None)
    items = getattr(models, "items", None) or []
    if items:
        total = getattr(models, "total_count", len(items))
        rows = [{
            "name": getattr(model, "name", "Unnamed"),
            "id": getattr(model, "id", "?"),
            "updated": _fmt_dt(getattr(model, "updated_at", None)),
        } for model in items]
        lines.append(f"## Models ({total})")
        lines.append("")
        lines.append(_md_table(rows, ["name", "id", "updated"]))
    else:
        lines.append("_No models in this project yet._")
    return "\n".join(lines)


def format_models(items: list, total: int, project_id: str, project_name: str) -> str:
    if not items:
        return f"Project **{project_name}** (`{project_id}`) has no models yet."
    rows = [{
        "name": getattr(model, "name", "Unnamed"),
        "id": getattr(model, "id", "?"),
        "updated": _fmt_dt(getattr(model, "updated_at", None)),
    } for model in items]
    table = _md_table(rows, ["name", "id", "updated"])
    return (
        f"## Models in {project_name} ({total} total)\n\n"
        f"Project: `{project_id}`\n\n{table}"
    )


def format_model_versions(model: Any, project_id: str) -> str:
    lines = [
        f"# Model: {getattr(model, 'name', 'Unnamed')}",
        "",
        f"- **ID:** `{getattr(model, 'id', '?')}`",
        f"- **Project:** `{project_id}`",
        f"- **Description:** {_clean(getattr(model, 'description', None))}",
        "",
    ]
    versions = getattr(model, "versions", None)
    items = getattr(versions, "items", None) or []
    if not items:
        lines.append("_No versions yet._")
        return "\n".join(lines)

    total = getattr(versions, "total_count", len(items))
    lines.append(f"## Versions ({total} total)")
    lines.append("")
    rows = []
    for version in items:
        author = getattr(version, "author_user", None)
        rows.append({
            "id": getattr(version, "id", "?"),
            "message": (getattr(version, "message", "") or "").strip() or "(no message)",
            "author": getattr(author, "name", "Unknown") if author else "Unknown",
            "source": getattr(version, "source_application", "") or "N/A",
            "created": _fmt_dt(getattr(version, "created_at", None)),
            "object": getattr(version, "referenced_object", "") or "",
        })
    lines.append(_md_table(rows, ["id", "message", "author", "source", "created", "object"]))
    lines.append("")
    lines.append("_Pass a version id above to `speckle_object_data` to fetch its object tree._")
    return "\n".join(lines)


def base_to_dict(base: Any, max_depth: int = 2, max_children: int = 25) -> Any:
    """Recursively convert a specklepy ``Base`` into a plain, size-capped structure.

    A ``Base`` is detected by its ``get_member_names`` method. Nesting beyond
    ``max_depth`` (including lists/dicts/tuples) is collapsed to a stub, and lists/dicts are truncated to
    ``max_children`` entries so a heavy geometry payload stays readable.
    """
    def convert(value: Any, depth: int) -> Any:
        get_members = getattr(value, "get_member_names", None)
        if callable(get_members):
            if depth > max_depth:
                return {
                    "speckle_type": getattr(value, "speckle_type", "Base"),
                    "id": getattr(value, "id", None),
                    "_truncated": "max depth reached",
                }
            result: dict[str, Any] = {}
            for name in get_members():
                result[name] = convert(getattr(value, name, None), depth + 1)
            return result
        if isinstance(value, (list, tuple)):
            if depth > max_depth:
                return {"_truncated": "max depth reached"}
            capped = [convert(item, depth + 1) for item in list(value)[:max_children]]
            if len(value) > max_children:
                capped.append(f"...(+{len(value) - max_children} more of {len(value)})")
            return capped
        if isinstance(value, dict):
            if depth > max_depth:
                return {"_truncated": "max depth reached"}
            trimmed = {k: convert(v, depth + 1) for k, v in list(value.items())[:max_children]}
            if len(value) > max_children:
                trimmed["_truncated"] = f"+{len(value) - max_children} more keys"
            return trimmed
        return value

    return convert(base, 0)


def format_object_data(
    version: Any,
    data: Any,
    project_id: str,
    max_depth: int,
    max_children: int,
) -> str:
    body = json.dumps(data, indent=2, default=str, ensure_ascii=False)
    truncated = ""
    if len(body) > _OBJECT_JSON_CHAR_LIMIT:
        body = body[:_OBJECT_JSON_CHAR_LIMIT]
        truncated = (
            f"\n\n_(JSON truncated at {_OBJECT_JSON_CHAR_LIMIT} chars — "
            "narrow with a lower max_depth or max_children)_"
        )
    return (
        f"# Object data for version `{getattr(version, 'id', '?')}`\n\n"
        f"- **Project:** `{project_id}`\n"
        f"- **Root object:** `{getattr(version, 'referenced_object', '?')}`\n"
        f"- **Source app:** {_clean(getattr(version, 'source_application', None))}\n"
        f"- **Caps:** depth {max_depth}, {max_children} children per collection\n\n"
        f"```json\n{body}\n```{truncated}"
    )

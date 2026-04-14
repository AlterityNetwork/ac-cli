"""Command registry — introspects the Typer app to produce a structured command tree."""

from __future__ import annotations

import functools
from typing import Any

import click
import typer.main

_WRITE_VERBS: set[str] = {
    "create",
    "update",
    "delete",
    "launch",
    "pause",
    "resume",
    "add",
    "remove",
    "approve",
    "reject",
    "regenerate",
    "archive",
    "unarchive",
    "assign",
    "snooze",
    "complete",
    "mark-read",
    "send",
    "upload",
    "install",
    "uninstall",
    "train",
    "feedback",
    "iterate",
    "analyze",
    "draft-email",
    "generate-draft",
    "reorder",
    "move",
    "order",
    "toggle",
    "duplicate",
    "preview",
    "commit",
    "bulk-upsert",
    "bulk-delete",
    "disconnect",
    "link",
    "set-current",
    "oauth-start",
    "update-draft",
    "update-status",
    "add-tags",
    "remove-tags",
    "reply",
    "update-config",
    "delete-config",
    "usage-event",
    "update-signature",
    "validate-signature",
    "retry-all",
    "retry-job",
    "clear-failed",
    "send-to-sentry",
    "scrape-website",
    "generate-org",
    "generate-profile",
    "prepare-account",
    "update-account",
    "delete-account",
    "cleanup",
    "send-link",
    "impersonate",
    "end-impersonation",
    "exit-impersonation",
    "activate",
    "deactivate",
    "update-settings",
    "reset-password",
    "generate-link",
    "add-member",
    "update-member",
    "remove-member",
    "transfer-ownership",
}

# Options that are CLI-framework concerns, not useful for agents
_SKIP_OPTIONS: set[str] = {"--help", "--json", "--yes", "-y", "-h", "--version", "-V"}


def _classify_command(name: str) -> str:
    """Classify a command as 'read' or 'write' based on its leaf name."""
    return "write" if name in _WRITE_VERBS else "read"


def _extract_params(command: click.Command) -> list[dict[str, Any]]:
    """Extract parameter metadata from a Click command."""
    params: list[dict[str, Any]] = []
    for param in command.params:
        # Skip framework options
        if isinstance(param, click.Option):
            if any(opt in _SKIP_OPTIONS for opt in param.opts):
                continue
            if any(opt in _SKIP_OPTIONS for opt in getattr(param, "secondary_opts", [])):
                continue

        type_name = param.type.name if hasattr(param.type, "name") else str(param.type)
        entry: dict[str, Any] = {
            "name": param.name or "",
            "type": type_name,
            "required": param.required,
        }

        if isinstance(param.type, click.Choice):
            entry["choices"] = list(param.type.choices)

        if isinstance(param, click.Option):
            entry["kind"] = "option"
            entry["flags"] = [o for o in param.opts if o not in _SKIP_OPTIONS]
        else:
            entry["kind"] = "argument"

        if param.default is not None and param.default != ():
            entry["default"] = param.default

        if param.help:
            entry["help"] = param.help

        params.append(entry)
    return params


def _walk_commands(
    group: click.Group | click.Command,
    path_parts: list[str],
    results: list[dict[str, Any]],
) -> None:
    """Recursively walk the Click command tree and collect leaf commands."""
    if isinstance(group, click.Group):
        for name in sorted(group.commands):
            child = group.commands[name]
            _walk_commands(child, [*path_parts, name], results)
    elif isinstance(group, click.Command):
        leaf_name = path_parts[-1] if path_parts else ""
        cmd_path = " ".join(path_parts)
        results.append({
            "path": cmd_path,
            "full_command": f"ac {cmd_path}",
            "help": (group.help or "").split("\n")[0].strip(),
            "mode": _classify_command(leaf_name),
            "params": _extract_params(group),
        })


@functools.lru_cache(maxsize=1)
def _build_registry_cached(app_id: int, app: typer.main.Typer) -> tuple[dict[str, Any], ...]:
    """Cached inner implementation. Uses app_id for hashability."""
    click_app = typer.main.get_command(app)
    results: list[dict[str, Any]] = []
    if isinstance(click_app, click.Group):
        for name in sorted(click_app.commands):
            child = click_app.commands[name]
            _walk_commands(child, [name], results)
    return tuple(results)


def build_registry(app: typer.main.Typer) -> list[dict[str, Any]]:
    """Build a complete command registry from a Typer app.

    Returns a list of command descriptors, each with path, help,
    mode (read/write), and params. Results are cached per app instance.
    """
    return list(_build_registry_cached(id(app), app))


def get_command_schema(app: typer.main.Typer, command_path: str) -> dict[str, Any] | None:
    """Get the schema for a single command by its dotted or spaced path.

    Accepts both "crm companies list" and "crm.companies.list".
    """
    normalized = command_path.replace(".", " ").strip()
    for entry in _build_registry_cached(id(app), app):
        if entry["path"] == normalized:
            return entry
    return None

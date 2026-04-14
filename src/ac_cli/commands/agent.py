"""Agent-optimized commands — machine-readable interface for AI agents."""

from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import typer

from ac_cli.formatting import print_json
from ac_cli.sdk.registry import build_registry, get_command_schema

app = typer.Typer(help="Agent-optimized commands (machine-readable output)")

_MAX_BATCH_SIZE = 16


@app.callback()
def agent_callback(ctx: typer.Context) -> None:
    ctx.ensure_object(dict)


def _get_app() -> typer.Typer:
    """Import the root app lazily to avoid circular imports."""
    from ac_cli.main import app as root_app

    return root_app


def _filter_fields(data: Any, fields: list[str]) -> Any:
    """Filter dict/list-of-dicts to only include specified fields."""
    if not fields:
        return data
    if isinstance(data, dict):
        if "data" in data and isinstance(data["data"], list):
            filtered = [{k: v for k, v in item.items() if k in fields} for item in data["data"] if isinstance(item, dict)]
            return {**data, "data": filtered}
        return {k: v for k, v in data.items() if k in fields}
    if isinstance(data, list):
        return [{k: v for k, v in item.items() if k in fields} for item in data if isinstance(item, dict)]
    return data


def _make_envelope(
    *,
    ok: bool,
    command: str,
    data: Any = None,
    error: str | None = None,
    duration_ms: int = 0,
) -> dict[str, Any]:
    """Build a consistent response envelope."""
    result: dict[str, Any] = {
        "ok": ok,
        "command": command,
    }
    if data is not None:
        result["data"] = data
    if error is not None:
        result["error"] = error
    result["duration_ms"] = duration_ms
    return result


def _run_cli_command(args: list[str]) -> tuple[str, str, int]:
    """Run a CLI command via subprocess and return (stdout, stderr, exit_code)."""
    import subprocess

    cmd = ["ac", *args]
    if "--json" not in cmd:
        cmd.append("--json")

    try:
        result = subprocess.run(  # nosec B603
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timed out after 30 seconds", -1
    except FileNotFoundError:
        return "", "ac CLI is not installed", -1


@app.command("commands")
def agent_commands(
    pretty: bool = typer.Option(False, "--pretty", help="Indent JSON output"),
    domain: str | None = typer.Option(None, "--domain", help="Filter to a specific domain (e.g. 'crm', 'envoy')"),
) -> None:
    """Output the full command tree as compact JSON.

    Auto-generated from Typer metadata — always in sync with the CLI.
    """
    registry = build_registry(_get_app())

    if domain:
        registry = [cmd for cmd in registry if cmd["path"].startswith(domain)]

    indent = 2 if pretty else None
    sys.stdout.write(json.dumps(registry, indent=indent, default=str) + "\n")


@app.command("help")
def agent_help(
    command_path: str = typer.Argument(..., help="Command path (e.g. 'crm companies list' or 'crm.companies.list')"),
) -> None:
    """Output detailed schema for a single command."""
    schema = get_command_schema(_get_app(), command_path)
    if schema is None:
        print_json({"error": True, "detail": f"Command not found: {command_path}"})
        raise typer.Exit(code=3)
    print_json(schema)


@app.command("exec")
def agent_exec(
    ctx: typer.Context,
    command_path: str = typer.Argument(..., help="Command path (e.g. 'crm.companies.list')"),
    fields: str | None = typer.Option(None, "--fields", help="Comma-separated fields to include in output"),
) -> None:
    """Execute a command with a consistent structured envelope.

    Auto-appends --json. Parses output into structured data.
    Pass extra flags after the command path.

    Example: ac agent exec crm.companies.list --fields id,name
    """
    cmd_args = command_path.replace(".", " ").split()

    remaining = ctx.args or []
    cmd_args.extend(remaining)

    t0 = time.monotonic()
    stdout, stderr, exit_code = _run_cli_command(cmd_args)
    duration_ms = round((time.monotonic() - t0) * 1000)

    if exit_code != 0:
        error_msg = stderr or stdout or "Command failed"
        print_json(_make_envelope(
            ok=False,
            command=command_path,
            error=error_msg,
            duration_ms=duration_ms,
        ))
        raise typer.Exit(code=exit_code if exit_code > 0 else 1)

    data: Any = stdout
    try:
        data = json.loads(stdout)
    except (json.JSONDecodeError, ValueError):
        pass

    if fields:
        field_list = [f.strip() for f in fields.split(",")]
        data = _filter_fields(data, field_list)

    print_json(_make_envelope(
        ok=True,
        command=command_path,
        data=data,
        duration_ms=duration_ms,
    ))


@app.command("batch")
def agent_batch(
    input_data: str | None = typer.Option(None, "--input", help="JSON array of command arrays"),
    fields: str | None = typer.Option(None, "--fields", help="Comma-separated fields to include in output"),
    max_parallel: int = typer.Option(_MAX_BATCH_SIZE, "--max-parallel", help="Max parallel commands"),
) -> None:
    """Execute multiple commands in parallel with structured output.

    Input format: JSON array of command path strings or arrays.
    Example: ac agent batch --input '[["crm.companies.list"], ["crm.deals.list"]]'

    Reads from stdin if --input is not provided.
    """
    raw_input = input_data
    if raw_input is None:
        raw_input = sys.stdin.read().strip()

    if not raw_input:
        print_json({"error": True, "detail": "No input provided"})
        raise typer.Exit(code=2)

    try:
        commands = json.loads(raw_input)
    except json.JSONDecodeError as e:
        print_json({"error": True, "detail": f"Invalid JSON: {e}"})
        raise typer.Exit(code=2)

    if not isinstance(commands, list):
        print_json({"error": True, "detail": "Input must be a JSON array"})
        raise typer.Exit(code=2)

    if len(commands) > max_parallel:
        print_json({"error": True, "detail": f"Too many commands (max {max_parallel})"})
        raise typer.Exit(code=2)

    field_list = [f.strip() for f in fields.split(",")] if fields else []

    def _exec_one(entry: Any) -> dict[str, Any]:
        if isinstance(entry, str):
            cmd_args = entry.replace(".", " ").split()
            cmd_path = entry
        elif isinstance(entry, list):
            cmd_args = []
            for part in entry:
                cmd_args.extend(str(part).replace(".", " ").split())
            cmd_path = " ".join(str(p) for p in entry)
        else:
            return _make_envelope(ok=False, command=str(entry), error="Invalid command format")

        t0 = time.monotonic()
        stdout, stderr, exit_code = _run_cli_command(cmd_args)
        duration_ms = round((time.monotonic() - t0) * 1000)

        if exit_code != 0:
            return _make_envelope(
                ok=False,
                command=cmd_path,
                error=stderr or stdout or "Command failed",
                duration_ms=duration_ms,
            )

        data: Any = stdout
        try:
            data = json.loads(stdout)
        except (json.JSONDecodeError, ValueError):
            pass

        if field_list:
            data = _filter_fields(data, field_list)

        return _make_envelope(ok=True, command=cmd_path, data=data, duration_ms=duration_ms)

    t0_total = time.monotonic()
    results: list[dict[str, Any]] = []
    workers = min(len(commands), max_parallel)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_exec_one, cmd): i for i, cmd in enumerate(commands)}
        indexed_results: list[tuple[int, dict[str, Any]]] = []
        for future in as_completed(futures):
            idx = futures[future]
            indexed_results.append((idx, future.result()))

    indexed_results.sort(key=lambda x: x[0])
    results = [r for _, r in indexed_results]

    total_duration_ms = round((time.monotonic() - t0_total) * 1000)
    print_json({"results": results, "total_duration_ms": total_duration_ms})

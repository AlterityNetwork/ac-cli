"""Managed agents run commands."""

from __future__ import annotations

import json
import sys
from collections.abc import Iterable
from typing import Any

import httpx
import typer
from rich import print as rprint

from ac_cli.client import get_api_client
from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    _handle_error,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.formatting import print_detail, print_json, print_table

app = typer.Typer(help="Managed agents")

_AGENTS = "/api/v1/agents"
_TERMINAL_STATUSES = {"completed", "failed", "expired", "cancelled"}

runs_app = typer.Typer(help="Managed agent run operations")


@app.callback()
def agents_callback(ctx: typer.Context) -> None:
    ctx.ensure_object(dict)


def _print_json_line(data: object) -> None:
    sys.stdout.write(json.dumps(data, separators=(",", ":"), default=str) + "\n")
    sys.stdout.flush()


def _iter_sse_payloads(lines: Iterable[str]) -> Iterable[tuple[str | None, str]]:
    event_id: str | None = None
    data_lines: list[str] = []

    def _flush() -> tuple[str | None, str] | None:
        nonlocal event_id, data_lines
        if not data_lines:
            event_id = None
            return None
        payload = "\n".join(data_lines)
        flushed = (event_id, payload)
        event_id = None
        data_lines = []
        return flushed

    for line in lines:
        if line == "":
            flushed = _flush()
            if flushed is not None:
                yield flushed
            continue
        if line.startswith(":"):
            continue
        if line.startswith("id:"):
            event_id = line[3:].strip()
            continue
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())

    flushed = _flush()
    if flushed is not None:
        yield flushed


def _render_watch_frame(frame: dict[str, Any], *, json_output: bool) -> int | None:
    event_type = str(frame.get("event_type") or "")
    status = str(frame.get("status") or "")
    data = frame.get("data") if isinstance(frame.get("data"), dict) else {}

    if json_output:
        _print_json_line(frame)
    elif event_type == "agent.message":
        text = str(data.get("text") or "")
        if text:
            sys.stdout.write(text)
            sys.stdout.flush()
    elif event_type == "run" and status in _TERMINAL_STATUSES:
        if status == "completed":
            rprint(f"\n[green]Run completed[/green] ({status})")
        else:
            detail = data.get("error") or status
            rprint(f"\n[red]Run finished with {status}:[/red] {detail}")
    elif event_type:
        rprint(f"[dim]{event_type}[/dim] status={status or '-'}")

    if event_type == "run" and status in _TERMINAL_STATUSES:
        return 0 if status == "completed" else 1
    return None


def _watch_run(run_id: str, *, json_output: bool) -> None:
    with get_api_client() as client:
        try:
            with client.stream(
                "GET",
                f"{_AGENTS}/runs/{run_id}/events",
                timeout=None,
            ) as resp:
                resp.raise_for_status()
                for event_id, payload in _iter_sse_payloads(resp.iter_lines()):
                    try:
                        frame = json.loads(payload)
                    except json.JSONDecodeError:
                        detail = {
                            "error": True,
                            "detail": "malformed_sse_frame",
                            "event_id": event_id,
                        }
                        if json_output:
                            _print_json_line(detail)
                        else:
                            rprint(
                                f"[yellow]Skipping malformed SSE frame[/yellow]"
                                f" event_id={event_id or '-'}"
                            )
                        continue
                    if not isinstance(frame, dict):
                        continue
                    exit_code = _render_watch_frame(frame, json_output=json_output)
                    if exit_code is not None:
                        raise typer.Exit(code=exit_code)
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)
        except httpx.HTTPError as exc:
            if json_output:
                _print_json_line({"error": True, "status_code": None, "detail": str(exc)})
            else:
                rprint(f"[red]Connection error:[/red] {exc}")
            raise typer.Exit(code=1)


@runs_app.command("create")
def runs_create(
    ctx: typer.Context,
    agent: str = typer.Option(..., "--agent", help="Agent name to run"),
    input_json: str | None = typer.Option(None, "--input", help="Input JSON string"),
    watch: bool = typer.Option(False, "--watch", help="Stream run events until terminal"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Enqueue a new agent run."""
    set_json_mode(json_output)
    body: dict = {"agent": agent, "input": {}}
    if input_json:
        try:
            body["input"] = json.loads(input_json)
        except json.JSONDecodeError:
            rprint("[red]Invalid JSON for --input[/red]")
            raise typer.Exit(code=1)

    resp = _api_request("post", f"{_AGENTS}/runs", json=body)

    data = resp.json()
    if json_output:
        if watch:
            _print_json_line(data)
        else:
            print_json(data)
    else:
        rprint(
            f"[green]Run created:[/green] {data['run_id']} "
            f"({data['agent']}, status: {data['status']})"
        )
    if watch:
        _watch_run(str(data["run_id"]), json_output=json_output)


@runs_app.command("get")
def runs_get(
    ctx: typer.Context,
    run_id: str = typer.Argument(..., help="Run ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get a agent run by ID."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_AGENTS}/runs/{run_id}")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(
        data,
        [
            ("run_id", "Run ID"),
            ("agent", "Agent"),
            ("status", "Status"),
            ("error", "Error"),
            ("created_at", "Created"),
            ("started_at", "Started"),
            ("finished_at", "Finished"),
        ],
    )


@runs_app.command("cancel")
def runs_cancel(
    ctx: typer.Context,
    run_id: str = typer.Argument(..., help="Run ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Cancel a queued or running agent run."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Cancel agent run {run_id}?", abort=True)

    resp = _api_request("post", f"{_AGENTS}/runs/{run_id}/cancel")

    data = resp.json()
    if json_output:
        print_json(data)
        return
    rprint(f"[green]Run cancelled:[/green] {data['run_id']} (status: {data['status']})")


@runs_app.command("watch")
def runs_watch(
    ctx: typer.Context,
    run_id: str = typer.Argument(..., help="Run ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Watch agent run events until the terminal frame."""
    set_json_mode(json_output)
    _watch_run(run_id, json_output=json_output)


@runs_app.command("list")
def runs_list(
    ctx: typer.Context,
    agent: str | None = typer.Option(None, "--agent", help="Filter by agent name"),
    status: str | None = typer.Option(None, "--status", help="Filter by run status"),
    limit: int = typer.Option(50, help="Max results"),
    offset: int = typer.Option(0, help="Offset"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List agent runs."""
    set_json_mode(json_output)
    params: dict = {"limit": limit, "offset": offset}
    if agent:
        params["agent"] = agent
    if status:
        params["status"] = status
    resp = _api_request("get", f"{_AGENTS}/runs", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("data", [])
    print_table(
        items,
        [
            ("run_id", "Run ID"),
            ("agent", "Agent"),
            ("status", "Status"),
            ("created_at", "Created"),
        ],
        title=f"Runs ({len(items)})",
    )


app.add_typer(runs_app, name="runs")

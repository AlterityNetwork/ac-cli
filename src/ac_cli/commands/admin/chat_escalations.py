"""Admin chat-escalations triage commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    _build_body,
    set_json_mode,
)
from ac_cli.commands.admin import _ADMIN
from ac_cli.formatting import print_json, print_table

chat_escalations_app = typer.Typer(help="Triage chat escalations (super admin)")


@chat_escalations_app.command("list")
def chat_escalations_list(
    ctx: typer.Context,
    status: str | None = typer.Option(
        None, help="Filter by status: open | triaged | resolved"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """List chat escalations across all orgs."""
    set_json_mode(json_output)
    params: dict = {}
    if status:
        params["status"] = status
    resp = _api_request("get", f"{_ADMIN}/chat-escalations", params=params)
    data = resp.json()
    if json_output:
        print_json(data)
        return
    items = data if isinstance(data, list) else data.get("data", [])
    print_table(
        items,
        [
            ("id", "ID"),
            ("organization_id", "Org"),
            ("thread_id", "Thread"),
            ("status", "Status"),
            ("created_at", "Created"),
        ],
        title=f"Chat Escalations ({len(items)})",
    )


@chat_escalations_app.command("update")
def chat_escalations_update(
    ctx: typer.Context,
    escalation_id: str = typer.Argument(..., help="Escalation ID"),
    status: str = typer.Option(..., help="open | triaged | resolved"),
    note: str | None = typer.Option(None, help="Optional triage note"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update an escalation's status (admin triage)."""
    set_json_mode(json_output)
    body = _build_body(status=status, note=note)
    resp = _api_request(
        "patch", f"{_ADMIN}/chat-escalations/{escalation_id}", json=body
    )
    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Updated escalation {escalation_id} → {status}[/green]")

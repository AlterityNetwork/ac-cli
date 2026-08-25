"""Agentic platform commands."""

from __future__ import annotations

from typing import Annotated

import typer

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.formatting import print_detail, print_json, print_table

app = typer.Typer(help="Agentic platform operations")

_APPROVALS = "/api/v1/agentic/approvals"

approvals_app = typer.Typer(help="Approval inbox — list, read, approve, reject")
app.add_typer(approvals_app, name="approvals")


@app.callback()
def agentic_callback(ctx: typer.Context) -> None:
    ctx.ensure_object(dict)


@approvals_app.callback()
def approvals_callback(ctx: typer.Context) -> None:
    ctx.ensure_object(dict)


@approvals_app.command("list")
def approvals_list(
    status: Annotated[
        str | None,
        typer.Option(
            "--status",
            help="Filter by display status: pending, expired, approved, rejected, cancelled",
        ),
    ] = None,
    cursor: Annotated[str | None, typer.Option("--cursor", help="Page cursor")] = None,
    limit: Annotated[int, typer.Option("--limit", help="Page size (1–100)")] = 50,
    json_output: bool = JSON_OPTION,
) -> None:
    """List approvals for your organization."""
    set_json_mode(json_output)
    params: dict[str, object] = {"limit": limit}
    if status is not None:
        params["status"] = status
    if cursor is not None:
        params["cursor"] = cursor
    resp = _api_request("get", _APPROVALS, params=params)
    data = resp.json()
    if json_output:
        print_json(data)
        return
    items = data.get("items", [])
    print_table(
        items,
        columns=[
            ("id", "ID"),
            ("action", "Action"),
            ("target_summary", "Target"),
            ("display_status", "Status"),
            ("created_at", "Created"),
        ],
        title="Approvals",
    )
    next_cursor = data.get("next_cursor")
    if next_cursor:
        typer.echo(f"Next page: --cursor {next_cursor}")


@approvals_app.command("read")
def approvals_read(
    approval_id: Annotated[str, typer.Argument(help="Approval ID")],
    json_output: bool = JSON_OPTION,
) -> None:
    """Read one approval by its ID."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_APPROVALS}/{approval_id}")
    data = resp.json()
    if json_output:
        print_json(data)
        return
    print_detail(
        data,
        fields=[
            ("id", "ID"),
            ("action", "Action"),
            ("target_summary", "Target"),
            ("display_status", "Status"),
            ("raised_by", "Raised by"),
            ("reason", "Reason"),
            ("preview", "Preview"),
            ("expires_at", "Expires"),
            ("resolved_by", "Resolved by"),
            ("resolved_at", "Resolved at"),
            ("created_at", "Created"),
        ],
    )


@approvals_app.command("approve")
def approvals_approve(
    approval_id: Annotated[str, typer.Argument(help="Approval ID")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
    json_output: bool = JSON_OPTION,
) -> None:
    """Approve one pending approval."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Approve approval {approval_id}?", abort=True)
    resp = _api_request("post", f"{_APPROVALS}/{approval_id}/approve")
    data = resp.json()
    if json_output:
        print_json(data)
        return
    typer.echo(f"Approved: {data.get('id')} (status: {data.get('display_status')})")


@approvals_app.command("reject")
def approvals_reject(
    approval_id: Annotated[str, typer.Argument(help="Approval ID")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
    json_output: bool = JSON_OPTION,
) -> None:
    """Reject one pending approval."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Reject approval {approval_id}?", abort=True)
    resp = _api_request("post", f"{_APPROVALS}/{approval_id}/reject")
    data = resp.json()
    if json_output:
        print_json(data)
        return
    typer.echo(f"Rejected: {data.get('id')} (status: {data.get('display_status')})")

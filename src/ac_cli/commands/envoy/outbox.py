"""Envoy outbox (draft approval flow) commands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich import print as rprint

from ac_cli.commands._helpers import JSON_OPTION, set_json_mode
from ac_cli.commands.crm import _CRM, _api_request, _build_body
from ac_cli.commands.envoy import _ENVOY
from ac_cli.formatting import print_json, print_table, styled

outbox_app = typer.Typer(help="Outbox / draft approval operations")


@outbox_app.command("pending")
def outbox_pending(
    ctx: typer.Context,
    sequence_id: str | None = typer.Option(None, "--sequence-id", help="Filter by sequence"),
    step_id: str | None = typer.Option(None, "--step-id", help="Filter by step"),
    limit: int = typer.Option(50, help="Max results"),
    offset: int = typer.Option(0, help="Pagination offset"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List pending draft approvals."""
    set_json_mode(json_output)
    params: dict = {"limit": limit, "offset": offset}
    if sequence_id:
        params["sequence_id"] = sequence_id
    if step_id:
        params["step_id"] = step_id

    resp = _api_request("get", f"{_ENVOY}/outbox/pending", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data.get("data", [])
    print_table(
        items,
        [
            ("recipient_name", "Recipient"),
            ("subject", "Subject"),
            ("sequence_name", "Sequence"),
            ("step_order", "Step"),
            ("id", "ID"),
        ],
        title=f"Pending Drafts ({data.get('total', '?')} total)",
    )


@outbox_app.command("sent")
def outbox_sent(
    ctx: typer.Context,
    sequence_id: str | None = typer.Option(None, "--sequence-id", help="Filter by sequence"),
    status: str | None = typer.Option(None, help="Filter by status"),
    limit: int = typer.Option(50, help="Max results"),
    offset: int = typer.Option(0, help="Pagination offset"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List sent emails."""
    set_json_mode(json_output)
    params: dict = {"limit": limit, "offset": offset}
    if sequence_id:
        params["sequence_id"] = sequence_id
    if status:
        params["status"] = status

    resp = _api_request("get", f"{_ENVOY}/outbox/sent", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data.get("data", [])
    print_table(
        items,
        [
            ("recipient_name", "Recipient"),
            ("subject", "Subject"),
            ("status", "Status"),
            ("sent_at", "Sent"),
            ("id", "ID"),
        ],
        title=f"Sent Emails ({data.get('total', '?')} total)",
    )


@outbox_app.command("step-drafts")
def outbox_step_drafts(
    ctx: typer.Context,
    sequence_id: str = typer.Option(..., "--sequence-id", help="Sequence ID"),
    step_id: str = typer.Option(..., "--step-id", help="Step ID"),
    limit: int = typer.Option(50, help="Max results"),
    offset: int = typer.Option(0, help="Pagination offset"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List all drafts for a specific step."""
    set_json_mode(json_output)
    params: dict = {
        "sequence_id": sequence_id,
        "step_id": step_id,
        "limit": limit,
        "offset": offset,
    }
    resp = _api_request("get", f"{_ENVOY}/outbox/step-drafts", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data.get("data", [])
    print_table(
        items,
        [
            ("recipient_name", "Recipient"),
            ("subject", "Subject"),
            ("status", "Status"),
            ("id", "ID"),
        ],
        title=f"Step Drafts ({data.get('total', '?')} total)",
    )


@outbox_app.command("update-draft")
def outbox_update_draft(
    ctx: typer.Context,
    draft_id: str = typer.Argument(..., help="Draft ID"),
    subject: str | None = typer.Option(None, help="New subject"),
    body: str | None = typer.Option(None, help="New body content"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update a pending draft."""
    set_json_mode(json_output)
    update_body = _build_body(subject=subject, body=body)

    if not update_body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    resp = _api_request("patch", f"{_ENVOY}/outbox/pending/{draft_id}", json=update_body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(styled("[green]Updated draft {}[/green]", draft_id))


@outbox_app.command("edit")
def outbox_edit(
    ctx: typer.Context,
    draft_id: str = typer.Argument(..., help="Draft (communication) ID"),
    subject: str | None = typer.Option(None, help="New subject"),
    body: str | None = typer.Option(
        None, help="New body content (mutually exclusive with --body-file)"
    ),
    body_file: Path | None = typer.Option(
        None,
        "--body-file",
        help="Path to a file whose contents become the new body",
        exists=True,
        dir_okay=False,
        readable=True,
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Save edits to a pending-approval draft without sending (ENG-712).

    Hits PATCH /crm/communications/{draft_id} — the canonical endpoint that
    also writes is_edited + edit_summary to communication_ai_metadata when
    subject or content actually change on an awaiting_approval row.
    """
    set_json_mode(json_output)

    if body is not None and body_file is not None:
        raise typer.BadParameter("--body and --body-file are mutually exclusive")
    if subject is None and body is None and body_file is None:
        raise typer.BadParameter("Provide at least one of --subject, --body, or --body-file")

    content = body_file.read_text() if body_file is not None else body
    update_body = _build_body(subject=subject, content=content)
    resp = _api_request("patch", f"{_CRM}/communications/{draft_id}", json=update_body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(styled("[green]Edited draft {}[/green]", draft_id))


@outbox_app.command("approve")
def outbox_approve(
    ctx: typer.Context,
    draft_id: str = typer.Argument(..., help="Draft ID"),
    subject: str | None = typer.Option(None, help="Override subject before sending"),
    body: str | None = typer.Option(None, help="Override body before sending"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Approve and send a pending draft."""
    set_json_mode(json_output)
    req_body = _build_body(subject=subject, body=body)
    resp = _api_request("post", f"{_ENVOY}/outbox/pending/{draft_id}/approve", json=req_body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(styled("[green]Approved and sent draft {}[/green]", draft_id))


@outbox_app.command("reject")
def outbox_reject(
    ctx: typer.Context,
    draft_id: str = typer.Argument(..., help="Draft ID"),
    action: str = typer.Option(
        ...,
        help="Action: regenerate, remove_recipient, skip_send, or manual_edit",
    ),
    reason: str | None = typer.Option(None, help="Reason for rejection"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Reject a pending draft."""
    set_json_mode(json_output)
    req_body = _build_body(action=action, reason=reason)
    resp = _api_request("post", f"{_CRM}/communications/{draft_id}/reject", json=req_body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(styled("[green]Rejected draft {} (action: {})[/green]", draft_id, action))


@outbox_app.command("regenerate")
def outbox_regenerate(
    ctx: typer.Context,
    draft_id: str = typer.Argument(..., help="Draft ID"),
    instruction: str | None = typer.Option(None, help="Instruction for regeneration"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Regenerate a draft with AI."""
    set_json_mode(json_output)
    req_body = _build_body(instruction=instruction)
    resp = _api_request("post", f"{_CRM}/communications/{draft_id}/regenerate", json=req_body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(styled("[green]Regenerated draft {}[/green]", draft_id))

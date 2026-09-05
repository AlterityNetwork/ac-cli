"""Envoy sequence recipients commands."""

from __future__ import annotations

import json as json_lib

import typer
from rich import print as rprint

from ac_cli.commands._helpers import JSON_OPTION, set_json_mode, should_skip_confirm
from ac_cli.commands.crm import _api_request
from ac_cli.commands.envoy import _ENVOY
from ac_cli.formatting import print_json, print_table, styled

recipients_app = typer.Typer(help="Sequence recipient operations")


@recipients_app.command("list")
def recipients_list(
    ctx: typer.Context,
    sequence_id: str = typer.Argument(..., help="Sequence ID"),
    status: str | None = typer.Option(None, help="Filter by status"),
    step_id: str | None = typer.Option(None, "--step-id", help="Filter by step"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List recipients of a sequence."""
    set_json_mode(json_output)
    params: dict = {}
    if status:
        params["status_filter"] = status
    if step_id:
        params["step_id"] = step_id

    resp = _api_request("get", f"{_ENVOY}/sequences/{sequence_id}/recipients", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("data", [])
    print_table(
        items,
        [
            ("recipient_name", "Name"),
            ("recipient_email", "Email"),
            ("status", "Status"),
            ("current_step", "Current Step"),
            ("id", "ID"),
        ],
        title=f"Recipients ({len(items)})",
    )


@recipients_app.command("add")
def recipients_add(
    ctx: typer.Context,
    sequence_id: str = typer.Argument(..., help="Sequence ID"),
    prospect_ids: str = typer.Option(
        None, "--prospect-ids", "-p", help="Comma-separated prospect IDs"
    ),
    crm_list_id: str | None = typer.Option(
        None, "--crm-list-id", help="CRM list ID to add members from"
    ),
    source: str | None = typer.Option(
        None, help="Raw JSON source object (advanced, overrides other options)"
    ),
    reenroll: bool = typer.Option(
        False,
        "--reenroll",
        "--force",
        help=(
            "Reactivate prospects previously removed/completed/errored in this "
            "sequence. Without this they are reported and skipped (ENG-1188)."
        ),
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Add recipients to a sequence from prospect IDs or a CRM list.

    Re-adding a prospect previously removed (or whose enrolment completed or
    errored) is not silent: it is reported under ``requires_confirmation`` and
    only reactivated with ``--reenroll`` (or after confirming the prompt).
    Re-adding an already-active prospect is a safe skip (ENG-1188).
    """
    set_json_mode(json_output)

    if source:
        try:
            body = json_lib.loads(source)
        except json_lib.JSONDecodeError:
            rprint("[red]Invalid JSON for --source[/red]")
            raise typer.Exit(code=1)
        # Wrap in {"source": ...} if not already wrapped
        if "source" not in body:
            body = {"source": body}
    elif prospect_ids:
        ids = [pid.strip() for pid in prospect_ids.split(",") if pid.strip()]
        body = {"source": {"type": "explicit", "prospect_ids": ids}}
    elif crm_list_id:
        body = {"source": {"type": "crm_list", "crm_list_id": crm_list_id}}
    else:
        rprint("[red]Provide --prospect-ids, --crm-list-id, or --source[/red]")
        raise typer.Exit(code=1)

    body["reenroll"] = reenroll

    resp = _api_request("post", f"{_ENVOY}/sequences/{sequence_id}/recipients", json=body)
    data = resp.json()

    if json_output:
        print_json(data)
        return

    added = data.get("added", []) if isinstance(data, dict) else []
    already_active = data.get("already_active", []) if isinstance(data, dict) else []
    needs_confirm = data.get("requires_confirmation", []) if isinstance(data, dict) else []

    # Previously-enrolled prospects: warn, then re-call with reenroll=true after
    # an explicit confirmation (honouring AC_YES) unless --reenroll was passed.
    if needs_confirm and not reenroll:
        names = ", ".join((p.get("full_name") or p.get("prospect_id", "?")) for p in needs_confirm)
        rprint(
            styled(
                "[yellow]{} prospect(s) were previously in this sequence (removed/completed/error) and were NOT re-added: {}[/yellow]",
                len(needs_confirm),
                names,
            )
        )
        rprint("[yellow]Re-adding them may send them outreach again.[/yellow]")
        proceed = should_skip_confirm(False) or typer.confirm(
            "Re-add these previously-contacted people?", default=False
        )
        if proceed:
            reenrol_ids = [p["prospect_id"] for p in needs_confirm]
            resp2 = _api_request(
                "post",
                f"{_ENVOY}/sequences/{sequence_id}/recipients",
                json={
                    "source": {"type": "explicit", "prospect_ids": reenrol_ids},
                    "reenroll": True,
                },
            )
            added = added + (resp2.json().get("added", []) or [])
            needs_confirm = []

    if added:
        rprint(
            styled("[green]Added {} recipient(s) to sequence {}[/green]", len(added), sequence_id)
        )
    if already_active:
        rprint(styled("[dim]{} already enrolled (skipped)[/dim]", len(already_active)))
    if needs_confirm:
        rprint(
            styled(
                "[yellow]{} previously-enrolled prospect(s) not re-added. Re-run with --reenroll to reactivate them.[/yellow]",
                len(needs_confirm),
            )
        )
    if not added and not already_active and not needs_confirm:
        rprint(styled("[yellow]No recipients added to sequence {}[/yellow]", sequence_id))


@recipients_app.command("remove")
def recipients_remove(
    sequence_id: str = typer.Argument(..., help="Sequence ID"),
    recipient_id: str = typer.Argument(..., help="Recipient ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Remove a recipient from a sequence."""
    if not should_skip_confirm(yes):
        typer.confirm(f"Remove recipient {recipient_id} from sequence {sequence_id}?", abort=True)

    _api_request("delete", f"{_ENVOY}/sequences/{sequence_id}/recipients/{recipient_id}")

    rprint(
        styled("[green]Removed recipient {} from sequence {}[/green]", recipient_id, sequence_id)
    )

"""Admin entitlement-grants commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    _build_body,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.commands.admin import _ADMIN
from ac_cli.formatting import print_json, print_table, styled

entitlement_grants_app = typer.Typer(
    help="Per-organization entitlement grants and the resolved snapshot (super admin)"
)


@entitlement_grants_app.command("list")
def grants_list(
    ctx: typer.Context,
    organization_id: str = typer.Option(..., "--org-id", help="Organization ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List an organization's grant rows and the keys they resolve to."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_ADMIN}/organizations/{organization_id}/entitlement-grants")
    data = resp.json()
    if json_output:
        print_json(data)
        return
    snapshot = data.get("snapshot") or {}
    rprint(
        styled("[bold]Resolved keys:[/bold] {}", ", ".join(snapshot.get("keys") or []) or "none")
    )
    rprint(
        styled(
            "[bold]Access:[/bold] {}   [bold]Credits:[/bold] {}",
            snapshot.get("access_mode"),
            (snapshot.get("credits") or {}).get("allowance"),
        )
    )
    items = data.get("grants") or []
    print_table(
        items,
        [
            ("key", "Key"),
            ("mode", "Mode"),
            ("source", "Source"),
            ("expires_at", "Expires"),
            ("id", "ID"),
        ],
        title=f"Entitlement Grants ({len(items)})",
    )


@entitlement_grants_app.command("create")
def grants_create(
    ctx: typer.Context,
    organization_id: str = typer.Option(..., "--org-id", help="Organization ID"),
    key: str = typer.Option(..., help="Commercial key, for example crm or chat"),
    source: str = typer.Option(..., help="plan_addon, trial or comp"),
    mode: str = typer.Option("grant", help="grant or revoke"),
    expires_at: str | None = typer.Option(
        None, "--expires-at", help="ISO 8601 instant with a timezone; required for a trial"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Add a grant or revoke row to an organization."""
    set_json_mode(json_output)
    body = _build_body(key=key, source=source, mode=mode, expires_at=expires_at)
    resp = _api_request(
        "post",
        f"{_ADMIN}/organizations/{organization_id}/entitlement-grants",
        json=body,
    )
    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(
            styled(
                "[green]Created {} row for {}:[/green] {}",
                data.get("mode"),
                data.get("key"),
                data.get("id"),
            )
        )


@entitlement_grants_app.command("delete")
def grants_delete(
    grant_id: str = typer.Argument(..., help="Grant row ID"),
    organization_id: str = typer.Option(..., "--org-id", help="Organization ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Remove a grant row."""
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete entitlement grant {grant_id}?", abort=True)
    _api_request(
        "delete",
        f"{_ADMIN}/organizations/{organization_id}/entitlement-grants/{grant_id}",
    )
    rprint(styled("[green]Deleted entitlement grant {}[/green]", grant_id))

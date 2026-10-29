"""Admin limit-overrides commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.commands.admin import _ADMIN
from ac_cli.formatting import as_text, print_detail, print_json, print_table, styled

limit_overrides_app = typer.Typer(
    help="Per-organization overrides of the numeric plan limits (super admin)"
)

_LIMIT_HELP = "The limit to override: email_sends_per_day"


@limit_overrides_app.command("list")
def overrides_list(
    ctx: typer.Context,
    organization_id: str = typer.Option(..., "--org-id", help="Organization ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List an organization's overrides, its plan limits and the resolved limits."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_ADMIN}/organizations/{organization_id}/limit-overrides")
    data = resp.json()
    if json_output:
        print_json(data)
        return
    plan = data.get("plan_limits") or {}
    limits = data.get("limits") or {}
    for name in sorted(set(plan) | set(limits)):
        rprint(
            styled(
                "[bold]{}:[/bold] plan {}   resolved {}",
                name,
                plan.get(name) if plan.get(name) is not None else "none",
                limits.get(name) if limits.get(name) is not None else "none",
            )
        )
    items = data.get("overrides") or []
    if not items:
        rprint(as_text("No overrides. The plan limits apply."))
        return
    print_table(
        items,
        [("limit_name", "Limit"), ("value", "Value"), ("updated_at", "Updated")],
        title=f"Limit overrides ({len(items)})",
    )


@limit_overrides_app.command("set")
def overrides_set(
    ctx: typer.Context,
    organization_id: str = typer.Option(..., "--org-id", help="Organization ID"),
    limit_name: str = typer.Option("email_sends_per_day", "--limit", help=_LIMIT_HELP),
    value: int = typer.Option(..., "--value", help="The limit for this organization"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Set the value of one limit for one organization, in place of the plan value."""
    set_json_mode(json_output)
    resp = _api_request(
        "put",
        f"{_ADMIN}/organizations/{organization_id}/limit-overrides/{limit_name}",
        json={"value": value},
    )
    data = resp.json()
    if json_output:
        print_json(data)
        return
    print_detail(data, [("limit_name", "Limit"), ("value", "Value"), ("updated_at", "Updated")])


@limit_overrides_app.command("clear")
def overrides_clear(
    ctx: typer.Context,
    organization_id: str = typer.Option(..., "--org-id", help="Organization ID"),
    limit_name: str = typer.Option("email_sends_per_day", "--limit", help=_LIMIT_HELP),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Remove an override, so the plan limit applies again."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(
            f"Remove the {limit_name} override of organization {organization_id}?",
            abort=True,
        )
    _api_request("delete", f"{_ADMIN}/organizations/{organization_id}/limit-overrides/{limit_name}")
    if json_output:
        print_json({"cleared": True, "limit_name": limit_name})
        return
    rprint(styled("[green]Cleared:[/green] {}", limit_name))

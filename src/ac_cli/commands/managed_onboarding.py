"""Managed onboarding commands (user-facing)."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import JSON_OPTION, _api_request, set_json_mode
from ac_cli.formatting import print_detail, print_json

app = typer.Typer(help="Managed onboarding")

_ONBOARD = "/api/v1/managed-onboarding"


@app.callback()
def onboarding_callback(ctx: typer.Context) -> None:
    ctx.ensure_object(dict)


@app.command("config")
def onboarding_config(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """Get onboarding configuration and status."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_ONBOARD}/config")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(
        data,
        [
            ("status", "Status"),
            ("org_name", "Organization"),
            ("completed_at", "Completed At"),
        ],
    )


@app.command("complete")
def onboarding_complete(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """Mark onboarding setup as complete."""
    set_json_mode(json_output)
    resp = _api_request("post", f"{_ONBOARD}/complete")

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint("[green]Onboarding marked as complete[/green]")

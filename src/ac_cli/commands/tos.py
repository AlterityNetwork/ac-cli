"""Terms of service commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import JSON_OPTION, _api_request, set_json_mode
from ac_cli.formatting import print_detail, print_json

app = typer.Typer(help="Terms of service")

_TOS = "/api/v1/tos"


@app.callback()
def tos_callback(ctx: typer.Context) -> None:
    ctx.ensure_object(dict)


@app.command("config")
def tos_config(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """Get current TOS configuration."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_TOS}/config")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(data, [
        ("version", "Version"), ("embed_url", "Embed URL"), ("updated_at", "Updated"),
    ])


@app.command("status")
def tos_status(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """Check if current user has accepted the latest TOS."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_TOS}/status")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    accepted = data.get("accepted", False)
    status = "[green]Accepted[/green]" if accepted else "[yellow]Not accepted[/yellow]"
    rprint(f"TOS Status: {status}")
    if data.get("version"):
        rprint(f"  Version: {data['version']}")


@app.command("accept")
def tos_accept(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """Accept the current TOS version."""
    set_json_mode(json_output)
    resp = _api_request("post", f"{_TOS}/accept")

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint("[green]TOS accepted[/green]")


@app.command("update-config")
def tos_update_config(
    ctx: typer.Context,
    version: str | None = typer.Option(None, "--version", help="New TOS version"),
    embed_url: str | None = typer.Option(None, "--embed-url", help="Termly embed URL"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update TOS configuration (superadmin only)."""
    set_json_mode(json_output)
    from ac_cli.commands._helpers import _build_body

    body = _build_body(version=version, embed_url=embed_url)
    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    resp = _api_request("patch", "/api/v1/admin/tos/config", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint("[green]TOS config updated[/green]")

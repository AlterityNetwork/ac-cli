"""Envoy campaigns commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    _build_body,
    _get_org_id,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.commands.envoy import _ENVOY
from ac_cli.formatting import print_detail, print_json, print_table

campaigns_app = typer.Typer(help="Campaign operations")


@campaigns_app.command("list")
def campaigns_list(
    ctx: typer.Context,
    archived: bool = typer.Option(False, "--archived", help="Show archived campaigns"),
    query: str | None = typer.Option(None, "--query", "-q", help="Search query"),
    limit: int | None = typer.Option(None, help="Max results"),
    offset: int | None = typer.Option(None, help="Row offset"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List campaigns."""
    set_json_mode(json_output)
    params: dict = {"archived": "true" if archived else "false"}
    if query:
        params["q"] = query
    if limit is not None:
        params["limit"] = limit
    if offset is not None:
        params["offset"] = offset

    resp = _api_request("get", f"{_ENVOY}/campaigns", params=params)
    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("data", [])
    print_table(
        items,
        [
            ("name", "Name"),
            ("goal", "Goal"),
            ("source_app", "Source"),
            ("sequence_count", "Sequences"),
            ("id", "ID"),
        ],
        title=f"Campaigns ({len(items)})",
    )


@campaigns_app.command("get")
def campaigns_get(
    ctx: typer.Context,
    campaign_id: str = typer.Argument(..., help="Campaign ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get a campaign by ID."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_ENVOY}/campaigns/{campaign_id}")
    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(
        data,
        [
            ("id", "ID"),
            ("name", "Name"),
            ("description", "Description"),
            ("goal", "Goal"),
            ("source_app", "Source App"),
            ("started_at", "Started"),
            ("ended_at", "Ended"),
            ("archived_at", "Archived"),
            ("sequence_count", "Sequences"),
            ("created_at", "Created"),
            ("updated_at", "Updated"),
        ],
    )


@campaigns_app.command("create")
def campaigns_create(
    ctx: typer.Context,
    name: str = typer.Option(..., help="Campaign name"),
    description: str | None = typer.Option(None, help="Description"),
    goal: str | None = typer.Option(None, help="Goal"),
    source_app: str | None = typer.Option(None, "--source-app", help="Source app slug"),
    started_at: str | None = typer.Option(None, "--started-at", help="ISO start date"),
    ended_at: str | None = typer.Option(None, "--ended-at", help="ISO end date"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create a new campaign."""
    set_json_mode(json_output)
    body = _build_body(
        name=name,
        description=description,
        goal=goal,
        source_app=source_app,
        started_at=started_at,
        ended_at=ended_at,
    )
    body["organization_id"] = _get_org_id()

    resp = _api_request("post", f"{_ENVOY}/campaigns", json=body)
    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Created campaign:[/green] {data['name']} ({data['id']})")


@campaigns_app.command("update")
def campaigns_update(
    ctx: typer.Context,
    campaign_id: str = typer.Argument(..., help="Campaign ID"),
    name: str | None = typer.Option(None, help="Campaign name"),
    description: str | None = typer.Option(None, help="Description"),
    goal: str | None = typer.Option(None, help="Goal"),
    source_app: str | None = typer.Option(None, "--source-app", help="Source app slug"),
    started_at: str | None = typer.Option(None, "--started-at", help="ISO start date"),
    ended_at: str | None = typer.Option(None, "--ended-at", help="ISO end date"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update a campaign."""
    set_json_mode(json_output)
    body = _build_body(
        name=name,
        description=description,
        goal=goal,
        source_app=source_app,
        started_at=started_at,
        ended_at=ended_at,
    )
    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    resp = _api_request("patch", f"{_ENVOY}/campaigns/{campaign_id}", json=body)
    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Updated campaign:[/green] {data['name']} ({data['id']})")


@campaigns_app.command("delete")
def campaigns_delete(
    campaign_id: str = typer.Argument(..., help="Campaign ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a campaign."""
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete campaign {campaign_id}?", abort=True)
    _api_request("delete", f"{_ENVOY}/campaigns/{campaign_id}")
    rprint(f"[green]Deleted campaign {campaign_id}[/green]")


@campaigns_app.command("archive")
def campaigns_archive(
    ctx: typer.Context,
    campaign_id: str = typer.Argument(..., help="Campaign ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Archive a campaign."""
    set_json_mode(json_output)
    resp = _api_request("post", f"{_ENVOY}/campaigns/{campaign_id}/archive")
    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Archived campaign {campaign_id}[/green]")


@campaigns_app.command("unarchive")
def campaigns_unarchive(
    ctx: typer.Context,
    campaign_id: str = typer.Argument(..., help="Campaign ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Unarchive a campaign."""
    set_json_mode(json_output)
    resp = _api_request("post", f"{_ENVOY}/campaigns/{campaign_id}/unarchive")
    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Unarchived campaign {campaign_id}[/green]")

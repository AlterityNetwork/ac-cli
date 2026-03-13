"""Envoy battlecards commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import _api_request, _build_body
from ac_cli.commands.envoy import _ENVOY
from ac_cli.formatting import print_detail, print_json, print_table

battlecards_app = typer.Typer(help="Battlecard operations")


@battlecards_app.command("list")
def battlecards_list(
    ctx: typer.Context,
    query: str | None = typer.Option(None, "--query", "-q", help="Search query"),
    limit: int | None = typer.Option(None, help="Max results"),
) -> None:
    """List battlecards."""
    params: dict = {}
    if query:
        params["q"] = query
    if limit is not None:
        params["limit"] = limit

    resp = _api_request("get", f"{_ENVOY}/battlecards", params=params)

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("data", [])
    print_table(
        items,
        [
            ("name", "Name"),
            ("competitor_name", "Competitor"),
            ("status", "Status"),
            ("id", "ID"),
        ],
        title=f"Battlecards ({len(items)})",
    )


@battlecards_app.command("get")
def battlecards_get(
    ctx: typer.Context,
    battlecard_id: str = typer.Argument(..., help="Battlecard ID"),
) -> None:
    """Get a battlecard by ID."""
    resp = _api_request("get", f"{_ENVOY}/battlecards/{battlecard_id}")

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
        return

    print_detail(data, [
        ("id", "ID"),
        ("name", "Name"),
        ("description", "Description"),
        ("competitor_name", "Competitor"),
        ("status", "Status"),
        ("strengths", "Strengths"),
        ("weaknesses", "Weaknesses"),
        ("created_at", "Created"),
        ("updated_at", "Updated"),
    ])


@battlecards_app.command("create")
def battlecards_create(
    ctx: typer.Context,
    name: str = typer.Option(..., help="Battlecard name"),
    description: str | None = typer.Option(None, help="Description"),
    competitor_name: str | None = typer.Option(None, "--competitor-name", help="Competitor name"),
    status: str | None = typer.Option(None, help="Status"),
) -> None:
    """Create a new battlecard."""
    body = _build_body(
        name=name, description=description, competitor_name=competitor_name,
        status=status,
    )

    me = _api_request("get", "/whoami")
    body["organization_id"] = me.json()["organization_id"]

    resp = _api_request("post", f"{_ENVOY}/battlecards", json=body)

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(f"[green]Created battlecard:[/green] {data['name']} ({data['id']})")


@battlecards_app.command("update")
def battlecards_update(
    ctx: typer.Context,
    battlecard_id: str = typer.Argument(..., help="Battlecard ID"),
    name: str | None = typer.Option(None, help="Battlecard name"),
    description: str | None = typer.Option(None, help="Description"),
    competitor_name: str | None = typer.Option(None, "--competitor-name", help="Competitor name"),
    status: str | None = typer.Option(None, help="Status"),
) -> None:
    """Update a battlecard."""
    body = _build_body(
        name=name, description=description, competitor_name=competitor_name,
        status=status,
    )

    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    resp = _api_request("patch", f"{_ENVOY}/battlecards/{battlecard_id}", json=body)

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(f"[green]Updated battlecard:[/green] {data['name']} ({data['id']})")


@battlecards_app.command("delete")
def battlecards_delete(
    battlecard_id: str = typer.Argument(..., help="Battlecard ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a battlecard."""
    if not yes:
        typer.confirm(f"Delete battlecard {battlecard_id}?", abort=True)

    _api_request("delete", f"{_ENVOY}/battlecards/{battlecard_id}")

    rprint(f"[green]Deleted battlecard {battlecard_id}[/green]")


@battlecards_app.command("duplicate")
def battlecards_duplicate(
    ctx: typer.Context,
    battlecard_id: str = typer.Argument(..., help="Battlecard ID"),
) -> None:
    """Duplicate a battlecard."""
    resp = _api_request("post", f"{_ENVOY}/battlecards/{battlecard_id}/duplicate")

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(f"[green]Duplicated battlecard:[/green] {data['name']} ({data['id']})")

"""Marketplace commands."""

from __future__ import annotations

import typer

from ac_cli.commands._helpers import JSON_OPTION, _api_request, set_json_mode
from ac_cli.formatting import print_detail, print_json, print_table

app = typer.Typer(help="App marketplace")

_MKT = "/api/v1/marketplace"


@app.callback()
def marketplace_callback(ctx: typer.Context) -> None:
    ctx.ensure_object(dict)


@app.command("list")
def apps_list(
    ctx: typer.Context,
    category: str | None = typer.Option(None, help="Filter by category"),
    status: str | None = typer.Option(None, help="Filter by status"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List marketplace apps."""
    set_json_mode(json_output)
    params: dict = {}
    if category:
        params["category"] = category
    if status:
        params["status"] = status

    resp = _api_request("get", f"{_MKT}/apps", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("apps", [])
    print_table(
        items,
        [("slug", "Slug"), ("name", "Name"), ("category", "Category"), ("status", "Status")],
        title=f"Marketplace Apps ({len(items)})",
    )


@app.command("get")
def apps_get(
    ctx: typer.Context,
    slug: str = typer.Argument(..., help="App slug"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get marketplace app details by slug."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_MKT}/apps/{slug}")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(
        data,
        [
            ("slug", "Slug"),
            ("name", "Name"),
            ("description", "Description"),
            ("category", "Category"),
            ("status", "Status"),
            ("developer_name", "Developer"),
        ],
    )


@app.command("developers")
def developers_list(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """List app developers."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_MKT}/developers")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("developers", [])
    print_table(
        items,
        [("id", "ID"), ("name", "Name"), ("app_count", "Apps")],
        title=f"Developers ({len(items)})",
    )

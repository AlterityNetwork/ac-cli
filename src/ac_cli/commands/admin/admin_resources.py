"""Admin resource (knowledge base) management commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import JSON_OPTION, _api_request, set_json_mode, should_skip_confirm
from ac_cli.commands.admin import _ADMIN
from ac_cli.formatting import print_detail, print_json, print_table

admin_resources_app = typer.Typer(help="Admin resource management")


@admin_resources_app.command("list")
def resources_list(
    ctx: typer.Context,
    org_id: str | None = typer.Option(None, "--org-id", help="Filter by organization ID"),
    limit: int = typer.Option(50, help="Max results"),
    offset: int = typer.Option(0, help="Offset"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List knowledge base resources."""
    set_json_mode(json_output)
    params: dict = {"limit": limit, "offset": offset}
    if org_id:
        params["org_id"] = org_id

    resp = _api_request("get", f"{_ADMIN}/resources", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data.get("data", data) if isinstance(data, dict) else data
    print_table(
        items if isinstance(items, list) else [items],
        [("id", "ID"), ("name", "Name"), ("status", "Status"), ("type", "Type")],
        title="Resources",
    )


@admin_resources_app.command("get")
def resources_get(
    ctx: typer.Context,
    resource_id: str = typer.Argument(..., help="Resource ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get a resource by ID."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_ADMIN}/resources/{resource_id}")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(
        data,
        [
            ("id", "ID"),
            ("name", "Name"),
            ("status", "Status"),
            ("type", "Type"),
            ("created_at", "Created"),
        ],
    )


@admin_resources_app.command("upload")
def resources_upload(
    ctx: typer.Context,
    file_path: str = typer.Argument(..., help="Path to file to upload"),
    org_id: str = typer.Option(..., "--org-id", help="Organization ID"),
    name: str | None = typer.Option(None, "--name", help="Resource name"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Upload a knowledge base resource."""
    set_json_mode(json_output)
    with open(file_path, "rb") as f:
        files = {"file": (file_path.split("/")[-1], f)}
        data_fields: dict = {"organization_id": org_id}
        if name:
            data_fields["name"] = name
        resp = _api_request("post", f"{_ADMIN}/resources/upload", files=files, data=data_fields)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Uploaded resource:[/green] {data.get('name', data.get('id', data))}")


@admin_resources_app.command("chunks")
def resources_chunks(
    ctx: typer.Context,
    resource_id: str = typer.Argument(..., help="Resource ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List chunks for a resource."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_ADMIN}/resources/{resource_id}/chunks")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("chunks", [])
    print_table(
        items, [("id", "ID"), ("index", "Index"), ("token_count", "Tokens")], title="Chunks"
    )


@admin_resources_app.command("preview-url")
def resources_preview_url(
    ctx: typer.Context,
    resource_id: str = typer.Argument(..., help="Resource ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get a presigned preview URL for a resource."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_ADMIN}/resources/{resource_id}/preview-url")

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Preview URL:[/green] {data.get('url', data)}")


@admin_resources_app.command("update")
def resources_update(
    ctx: typer.Context,
    resource_id: str = typer.Argument(..., help="Resource ID"),
    name: str | None = typer.Option(None, "--name", help="Resource name"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update a resource."""
    set_json_mode(json_output)
    from ac_cli.commands._helpers import _build_body

    body = _build_body(name=name)
    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    resp = _api_request("patch", f"{_ADMIN}/resources/{resource_id}", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Updated resource {resource_id}[/green]")


@admin_resources_app.command("delete")
def resources_delete(
    resource_id: str = typer.Argument(..., help="Resource ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a resource."""
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete resource {resource_id}?", abort=True)

    _api_request("delete", f"{_ADMIN}/resources/{resource_id}")

    rprint(f"[green]Deleted resource {resource_id}[/green]")


@admin_resources_app.command("reprocess")
def resources_reprocess(
    ctx: typer.Context,
    resource_id: str = typer.Argument(..., help="Resource ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Reprocess a resource (re-chunk and re-embed)."""
    set_json_mode(json_output)
    resp = _api_request("post", f"{_ADMIN}/resources/{resource_id}/reprocess")

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Reprocessing resource {resource_id}[/green]")

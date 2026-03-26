"""Knowledge base resource commands."""

from __future__ import annotations

import mimetypes
from pathlib import Path

import typer
from rich import print as rprint

from ac_cli.commands._helpers import JSON_OPTION, _api_request, _build_body, set_json_mode, should_skip_confirm
from ac_cli.formatting import print_detail, print_json, print_table

app = typer.Typer(help="Knowledge base resources")

_RESOURCES = "/api/v1/resources"

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}
MAX_SIZE_BYTES = 10_485_760  # 10 MB


@app.callback()
def resources_callback(ctx: typer.Context) -> None:
    ctx.ensure_object(dict)


@app.command("list")
def resources_list(
    ctx: typer.Context,
    limit: int = typer.Option(50, help="Max items to return"),
    offset: int = typer.Option(0, help="Offset for pagination"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List knowledge base resources."""
    set_json_mode(json_output)
    resp = _api_request("get", _RESOURCES, params={"limit": limit, "offset": offset})

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data.get("data", [])
    if not items:
        rprint("[dim]No resources found.[/dim]")
        return

    print_table(
        items,
        [
            ("id", "ID"),
            ("source_name", "Source Name"),
            ("status", "Status"),
            ("created_at", "Created"),
        ],
        title=f"Resources ({data.get('total', '?')} total)",
    )


@app.command("upload")
def resources_upload(
    ctx: typer.Context,
    file_path: Path = typer.Argument(..., help="Path to the resource file"),
    name: str = typer.Option(..., "--name", help="Source name for the resource"),
    description: str | None = typer.Option(None, "--description", help="Resource description"),
    tags: str | None = typer.Option(None, "--tags", help="Comma-separated tags"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Upload a knowledge base resource file."""
    set_json_mode(json_output)
    if not file_path.exists():
        rprint(f"[red]Error:[/red] File not found: {file_path}")
        raise typer.Exit(code=1)

    suffix = file_path.suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        rprint(f"[red]Error:[/red] Unsupported file type: {suffix}")
        raise typer.Exit(code=1)

    size = file_path.stat().st_size
    if size > MAX_SIZE_BYTES:
        rprint(f"[red]Error:[/red] File too large ({size} bytes, max {MAX_SIZE_BYTES})")
        raise typer.Exit(code=1)

    content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"

    form_data: dict = {"source_name": name}
    if description is not None:
        form_data["description"] = description
    if tags is not None:
        form_data["tags"] = tags

    with open(file_path, "rb") as f:
        resp = _api_request(
            "post",
            f"{_RESOURCES}/upload",
            files={"file": (file_path.name, f, content_type)},
            data=form_data,
        )

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Uploaded resource:[/green] {data.get('source_name', name)} ({data.get('id', '')})")


@app.command("delete")
def resources_delete(
    ctx: typer.Context,
    resource_id: str = typer.Argument(..., help="Resource ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Delete a knowledge base resource."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete resource {resource_id}?", abort=True)

    _api_request("delete", f"{_RESOURCES}/{resource_id}")

    if json_output:
        print_json({"deleted": True, "id": resource_id})
    else:
        rprint(f"[green]Deleted resource {resource_id}[/green]")


@app.command("status")
def resources_status(
    ctx: typer.Context,
    resource_id: str = typer.Argument(..., help="Resource ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get processing status for a knowledge base resource."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_RESOURCES}/{resource_id}/status")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(data, [
        ("id", "ID"),
        ("status", "Status"),
        ("chunk_count", "Chunk Count"),
        ("error_message", "Error"),
    ])

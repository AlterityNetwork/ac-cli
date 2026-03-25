"""CRM import commands."""

import json as json_lib
from pathlib import Path

import typer
from rich import print as rprint

from ac_cli.commands._helpers import JSON_OPTION, set_json_mode
from ac_cli.commands.crm import _CRM, _api_request
from ac_cli.formatting import print_json, print_table

imports_app = typer.Typer(help="Import operations")


@imports_app.command("preview")
def import_preview(
    ctx: typer.Context,
    file: Path = typer.Option(..., help="Path to JSON file with items to import"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Preview an import from a JSON file."""
    set_json_mode(json_output)
    if not file.exists():
        rprint(f"[red]File not found:[/red] {file}")
        raise typer.Exit(code=1)

    try:
        items = json_lib.loads(file.read_text())
    except json_lib.JSONDecodeError:
        rprint(f"[red]Invalid JSON in file:[/red] {file}")
        raise typer.Exit(code=1)
    resp = _api_request("post", f"{_CRM}/import/preview", json=items)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    preview_id = data.get("preview_id", "?")
    rprint(f"\n[bold]Import Preview[/bold] (ID: {preview_id})\n")

    summary = data.get("summary", {})
    rprint(f"  New records: {summary.get('new', 0)}")
    rprint(f"  Updates: {summary.get('updates', 0)}")
    rprint(f"  Skipped: {summary.get('skipped', 0)}")
    rprint(f"  Errors: {summary.get('errors', 0)}")

    records = data.get("records", [])
    if records:
        print_table(
            records[:20],
            [
                ("action", "Action"),
                ("entity_type", "Type"),
                ("name", "Name"),
                ("reason", "Reason"),
            ],
            title="Preview Records (first 20)",
        )

    rprint(f"\n[dim]Use 'ac crm import commit --preview-id {preview_id}' to apply[/dim]")


@imports_app.command("commit")
def import_commit(
    ctx: typer.Context,
    preview_id: str = typer.Option(..., "--preview-id", help="Preview ID from import preview"),
    auto_accept: bool = typer.Option(False, "--auto-accept", help="Auto-accept all changes"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Commit a previewed import."""
    set_json_mode(json_output)
    body = {"preview_id": preview_id, "auto_accept": auto_accept}
    resp = _api_request("post", f"{_CRM}/import/commit", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        created = data.get("created", 0)
        updated = data.get("updated", 0)
        rprint(f"[green]Import committed:[/green] {created} created, {updated} updated")

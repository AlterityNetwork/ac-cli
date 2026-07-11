"""CRM import commands."""

import json as json_lib
import uuid
from collections import Counter
from pathlib import Path

import typer
from rich import print as rprint

from ac_cli.commands._helpers import JSON_OPTION, _get_org_id, set_json_mode
from ac_cli.commands.crm import _CRM, _api_request
from ac_cli.formatting import print_json, print_table

imports_app = typer.Typer(help="Import operations")


@imports_app.command("preview")
def import_preview(
    ctx: typer.Context,
    file: Path = typer.Option(
        ...,
        help=(
            "Path to a JSON file containing a list of items to preview, each "
            "shaped as {app_slug, entity_type, raw_item, relationships?}."
        ),
    ),
    flow_run_id: str | None = typer.Option(
        None,
        "--flow-run-id",
        help="Originating flow run UUID. A random UUID is generated when omitted.",
    ),
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

    body = {
        "organization_id": _get_org_id(),
        "flow_run_id": flow_run_id or str(uuid.uuid4()),
        "items": items,
    }
    resp = _api_request("post", f"{_CRM}/import/preview", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    preview_id = data.get("preview_id", "?")
    rprint(f"\n[bold]Import Preview[/bold] (ID: {preview_id})\n")

    preview_items = data.get("items", [])
    counts = Counter(i.get("proposed_action", "?") for i in preview_items)
    rprint(f"  Create: {counts.get('create', 0)}")
    rprint(f"  Merge: {counts.get('merge', 0)}")
    rprint(f"  Skip: {counts.get('skip', 0)}")

    if preview_items:
        rows = []
        for item in preview_items[:20]:
            payload = item.get("normalized_payload") or {}
            rows.append(
                {
                    "proposed_action": item.get("proposed_action"),
                    "entity_type": item.get("entity_type"),
                    "name": payload.get("name") or payload.get("full_name") or "",
                    "action_reason": item.get("action_reason"),
                    "preview_item_id": item.get("preview_item_id"),
                }
            )
        print_table(
            rows,
            [
                ("proposed_action", "Action"),
                ("entity_type", "Type"),
                ("name", "Name"),
                ("action_reason", "Reason"),
                ("preview_item_id", "Item ID"),
            ],
            title="Preview Items (first 20)",
        )

    rprint(
        "\n[dim]Save this preview (rerun with --json > preview.json) and run "
        "'ac crm import commit --preview-file preview.json' to apply[/dim]"
    )


@imports_app.command("commit")
def import_commit(
    ctx: typer.Context,
    preview_file: Path = typer.Option(
        ...,
        "--preview-file",
        help="Path to the JSON preview output (from 'ac crm import preview --json').",
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Commit a previewed import by accepting each item's proposed action."""
    set_json_mode(json_output)
    if not preview_file.exists():
        rprint(f"[red]File not found:[/red] {preview_file}")
        raise typer.Exit(code=1)

    try:
        preview = json_lib.loads(preview_file.read_text())
    except json_lib.JSONDecodeError:
        rprint(f"[red]Invalid JSON in file:[/red] {preview_file}")
        raise typer.Exit(code=1)

    preview_id = preview.get("preview_id")
    if not preview_id:
        rprint("[red]Preview file is missing 'preview_id'[/red]")
        raise typer.Exit(code=1)

    decisions = []
    for item in preview.get("items", []):
        final_action = item.get("proposed_action", "skip")
        decision: dict = {
            "preview_item_id": item["preview_item_id"],
            "final_action": final_action,
        }
        match_info = item.get("match_info") or {}
        matched_id = match_info.get("matched_id")
        if final_action == "merge" and matched_id:
            decision["target_id"] = matched_id
        decisions.append(decision)

    body = {"preview_id": preview_id, "decisions": decisions}
    resp = _api_request("post", f"{_CRM}/import/commit", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    results = data.get("results", [])
    counts = Counter(r.get("status", "?") for r in results)
    rprint(
        f"[green]Import committed:[/green] "
        f"{counts.get('created', 0)} created, "
        f"{counts.get('merged', 0)} merged, "
        f"{counts.get('skipped', 0)} skipped, "
        f"{counts.get('failed', 0)} failed"
    )

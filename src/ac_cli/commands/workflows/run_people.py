"""Workflow run-people commands: list, add-to-crm, delete, count, company-match, search."""

from __future__ import annotations

import httpx
import typer
from rich import print as rprint

from ac_cli.client import get_api_client
from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    _handle_error,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.commands.workflows import _WORKFLOWS
from ac_cli.formatting import print_json, print_table

run_people_app = typer.Typer(help="Workflow-discovered people operations")


@run_people_app.command("list")
def run_people_list(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    limit: int = typer.Option(50, help="Max results"),
    offset: int = typer.Option(0, help="Offset"),
    include_in_crm: bool = typer.Option(
        False, "--include-in-crm", help="Include people already in CRM"
    ),
    sort_by: str | None = typer.Option(
        None,
        "--sort-by",
        help=(
            "Sort column: 'relevance_score' (API default, strongest role match "
            "first) or 'discovered_at' (newest first). Omit for the API default."
        ),
    ),
    sort_dir: str | None = typer.Option(
        None, "--sort-dir", help="Sort direction: 'desc' (default) or 'asc'"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """List people discovered by a workflow (deduplicated)."""
    set_json_mode(json_output)
    params: dict = {"limit": limit, "offset": offset, "include_in_crm": include_in_crm}
    if sort_by is not None:
        params["sort_by"] = sort_by
    if sort_dir is not None:
        params["sort_dir"] = sort_dir
    resp = _api_request("get", f"{_WORKFLOWS}/{workflow_id}/runs/people", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_table(
        data.get("data", []),
        [
            ("full_name", "Name"),
            ("email", "Email"),
            ("current_title", "Title"),
            ("current_company_text", "Company"),
            ("id", "ID"),
        ],
        title=f"Workflow People ({data.get('total', '?')} total)",
    )
    filter_options = data.get("filter_options") or {}
    if filter_options:
        rprint(
            "Filter options: "
            f"{len(filter_options.get('titles', []))} titles, "
            f"{len(filter_options.get('locations', []))} locations, "
            f"{len(filter_options.get('sources', []))} sources"
        )


@run_people_app.command("list-by-run")
def run_people_list_by_run(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    run_id: str = typer.Argument(..., help="Run ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List people from a specific run (no deduplication)."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_WORKFLOWS}/{workflow_id}/runs/{run_id}/people")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("data", [])
    print_table(
        items,
        [
            ("full_name", "Name"),
            ("email", "Email"),
            ("current_title", "Title"),
            ("current_company_text", "Company"),
            ("id", "ID"),
        ],
        title=f"Run People ({len(items)} total)",
    )


@run_people_app.command("company-match-preview")
def run_people_company_match_preview(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    person_ids: str = typer.Option(..., "--person-ids", help="Comma-separated workflow person IDs"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Preview company matches for workflow people."""
    set_json_mode(json_output)
    ids_list = [i.strip() for i in person_ids.split(",") if i.strip()]
    resp = _api_request(
        "post",
        f"{_WORKFLOWS}/{workflow_id}/runs/people/company-match-preview",
        json={"person_ids": ids_list},
    )

    data = resp.json()
    if json_output:
        print_json(data)
        return

    matches = data.get("matches", [])
    print_table(
        matches,
        [
            ("company_text", "Company"),
            ("person_count", "People"),
            ("match_source", "Source"),
            ("match_type", "Match Type"),
        ],
        title=f"Company Match Preview ({len(matches)} matches)",
    )
    no_company = data.get("no_company_person_ids", [])
    if no_company:
        rprint(f"\n[yellow]{len(no_company)} people have no company info[/yellow]")


@run_people_app.command("company-search")
def run_people_company_search(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    query: str = typer.Option("", "--query", "-q", help="Search query"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Search CRM and Sonar companies by name."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_WORKFLOWS}/{workflow_id}/company-search", params={"q": query})

    data = resp.json()
    if json_output:
        print_json(data)
        return

    results = data.get("results", [])
    print_table(
        results,
        [
            ("source", "Source"),
            ("name", "Name"),
            ("industry", "Industry"),
            ("location", "Location"),
            ("id", "ID"),
        ],
        title=f"Company Search ({len(results)} results)",
    )


@run_people_app.command("add-to-crm")
def run_people_add_to_crm(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    person_ids: str = typer.Option(..., "--person-ids", help="Comma-separated workflow person IDs"),
    overrides_file: str | None = typer.Option(
        None, "--overrides-file", help="JSON file with company overrides"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Add workflow-discovered people to CRM."""
    import json as json_mod
    from pathlib import Path

    set_json_mode(json_output)
    ids_list = [i.strip() for i in person_ids.split(",") if i.strip()]
    body: dict = {"person_ids": ids_list}

    if overrides_file:
        path = Path(overrides_file)
        if not path.exists():
            rprint(f"[red]File not found:[/red] {overrides_file}")
            raise typer.Exit(code=1)
        try:
            body["company_overrides"] = json_mod.loads(path.read_text())
        except json_mod.JSONDecodeError:
            rprint("[red]Invalid JSON in overrides file[/red]")
            raise typer.Exit(code=1)

    resp = _api_request(
        "post",
        f"{_WORKFLOWS}/{workflow_id}/runs/people/add-to-crm",
        json=body,
    )

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(
            f"[green]Synced {data.get('synced_count', 0)} people to CRM[/green]"
            f" (new: {data.get('added_count', 0)},"
            f" linked: {data.get('skipped_count', 0)})"
        )


@run_people_app.command("add-to-list")
def run_people_add_to_list(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    person_ids: str = typer.Option(..., "--person-ids", help="Comma-separated workflow person IDs"),
    list_id: str = typer.Option(..., "--list-id", help="Target CRM list ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Add workflow people to a list (auto-syncs them to CRM first if needed)."""
    set_json_mode(json_output)
    ids_list = [i.strip() for i in person_ids.split(",") if i.strip()]
    resp = _api_request(
        "post",
        f"{_WORKFLOWS}/{workflow_id}/runs/people/add-to-list",
        json={"person_ids": ids_list, "list_id": list_id},
    )

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(
            f"[green]Added {data.get('added_count', 0)} people to list[/green]"
            f" (synced: {data.get('synced_count', 0)},"
            f" already in list: {data.get('already_member_count', 0)},"
            f" skipped removed: {len(data.get('skipped_deleted_ids', []))})"
        )


@run_people_app.command("add-to-sequence")
def run_people_add_to_sequence(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    person_ids: str = typer.Option(..., "--person-ids", help="Comma-separated workflow person IDs"),
    sequence_id: str = typer.Option(..., "--sequence-id", help="Target sequence ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Enrol workflow people into a sequence (auto-syncs them to CRM first)."""
    set_json_mode(json_output)
    ids_list = [i.strip() for i in person_ids.split(",") if i.strip()]
    resp = _api_request(
        "post",
        f"{_WORKFLOWS}/{workflow_id}/runs/people/add-to-sequence",
        json={"person_ids": ids_list, "sequence_id": sequence_id},
    )

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(
            f"[green]Enrolled {data.get('added_count', 0)} people in sequence[/green]"
            f" (synced: {data.get('synced_count', 0)},"
            f" already active: {data.get('already_active_count', 0)},"
            f" needs confirmation: {data.get('requires_confirmation_count', 0)},"
            f" skipped removed: {len(data.get('skipped_deleted_ids', []))})"
        )


@run_people_app.command("crm-count")
def run_people_crm_count(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get count of people added to CRM for a workflow."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_WORKFLOWS}/{workflow_id}/runs/people/added-to-crm-count")

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"People added to CRM: [bold]{data.get('count', 0)}[/bold]")


@run_people_app.command("delete")
def run_people_delete(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    person_ids: str = typer.Option(..., "--person-ids", help="Comma-separated workflow person IDs"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Delete workflow-discovered people."""
    set_json_mode(json_output)
    ids_list = [i.strip() for i in person_ids.split(",") if i.strip()]
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete {len(ids_list)} workflow people?", abort=True)

    # httpx delete() doesn't accept json body; use request() directly
    with get_api_client() as client:
        try:
            resp = client.request(
                "DELETE",
                f"{_WORKFLOWS}/{workflow_id}/runs/people",
                json={"person_ids": ids_list},
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)
        except httpx.HTTPError as exc:
            rprint(f"[red]Connection error:[/red] {exc}")
            raise typer.Exit(code=1)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Deleted {data.get('deleted_count', 0)} workflow people[/green]")

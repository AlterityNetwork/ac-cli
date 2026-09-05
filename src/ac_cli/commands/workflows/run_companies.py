"""Workflow run-companies commands: list, add-to-crm, delete, count."""

from __future__ import annotations

import httpx
import typer
from rich import print as rprint

from ac_cli.client import get_api_client
from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    _handle_connection_error,
    _handle_error,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.commands.workflows import _WORKFLOWS
from ac_cli.formatting import print_json, print_table, styled

run_companies_app = typer.Typer(help="Workflow-discovered company operations")


@run_companies_app.command("list")
def run_companies_list(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    limit: int = typer.Option(50, help="Max results"),
    offset: int = typer.Option(0, help="Offset"),
    include_in_crm: bool = typer.Option(
        False, "--include-in-crm", help="Include companies already in CRM"
    ),
    sort_by: str | None = typer.Option(
        None,
        "--sort-by",
        help=(
            "Sort column: discovered_at (default, newest first) or "
            "lead_score (highest first — use for 'hottest signals' / "
            "'top-scoring companies' queries)."
        ),
    ),
    approved: bool | None = typer.Option(
        None,
        "--approved/--unapproved",
        help=(
            "ENG-912 Actioned filter. --unapproved hides rows whose "
            "linked CRM company has been Actioned (any of note, manual "
            "outbound comm, list-add, sequence-enrol); --approved shows "
            "only Actioned rows. Omit for the union of both."
        ),
    ),
    min_lead_score: float | None = typer.Option(
        None,
        "--min-lead-score",
        min=0,
        max=10,
        help=(
            "Relevance floor (Sonar inbox 'hide low-relevance' toggle). "
            "Hides companies whose merged lead_score is below this value; "
            "unscored companies stay visible. Omit to show all scores."
        ),
    ),
    crm_company_ids: str | None = typer.Option(
        None,
        "--crm-company-ids",
        help=(
            "Comma-separated CRM company ids. Only returns companies linked "
            "to one of these, to resolve the envelopes behind a set of signals."
        ),
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """List companies discovered by a workflow (deduplicated)."""
    set_json_mode(json_output)
    params: dict = {"limit": limit, "offset": offset, "include_in_crm": include_in_crm}
    if sort_by:
        params["sort_by"] = sort_by
    if approved is not None:
        params["approved"] = approved
    if min_lead_score is not None:
        params["min_lead_score"] = min_lead_score
    if crm_company_ids:
        params["crm_company_ids"] = crm_company_ids
    resp = _api_request("get", f"{_WORKFLOWS}/{workflow_id}/runs/companies", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_table(
        data.get("data", []),
        [
            ("name", "Name"),
            ("industry", "Industry"),
            ("location", "Location"),
            ("id", "ID"),
        ],
        title=f"Workflow Companies ({data.get('total', '?')} total)",
    )


@run_companies_app.command("list-by-run")
def run_companies_list_by_run(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    run_id: str = typer.Argument(..., help="Run ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List companies from a specific run (no deduplication)."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_WORKFLOWS}/{workflow_id}/runs/{run_id}/companies")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("data", [])
    print_table(
        items,
        [
            ("name", "Name"),
            ("industry", "Industry"),
            ("location", "Location"),
            ("id", "ID"),
        ],
        title=f"Run Companies ({len(items)} total)",
    )


@run_companies_app.command("add-to-crm")
def run_companies_add_to_crm(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    company_ids: str = typer.Option(
        ..., "--company-ids", help="Comma-separated workflow company IDs"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Add workflow-discovered companies to CRM."""
    set_json_mode(json_output)
    ids_list = [i.strip() for i in company_ids.split(",") if i.strip()]
    resp = _api_request(
        "post",
        f"{_WORKFLOWS}/{workflow_id}/runs/companies/add-to-crm",
        json={"company_ids": ids_list},
    )

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(
            styled(
                "[green]Synced {} companies to CRM[/green] (new: {}, updated: {}, skipped: {})",
                data.get("synced_count", 0),
                data.get("added_count", 0),
                data.get("updated_count", 0),
                data.get("skipped_count", 0),
            )
        )


@run_companies_app.command("add-to-list")
def run_companies_add_to_list(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    company_ids: str = typer.Option(
        ..., "--company-ids", help="Comma-separated workflow company IDs"
    ),
    list_id: str = typer.Option(..., "--list-id", help="Target CRM list ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Add workflow companies to a list (auto-syncs them to CRM first if needed)."""
    set_json_mode(json_output)
    ids_list = [i.strip() for i in company_ids.split(",") if i.strip()]
    resp = _api_request(
        "post",
        f"{_WORKFLOWS}/{workflow_id}/runs/companies/add-to-list",
        json={"company_ids": ids_list, "list_id": list_id},
    )

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(
            styled(
                "[green]Added {} companies to list[/green] (synced: {}, already in list: {}, skipped removed: {})",
                data.get("added_count", 0),
                data.get("synced_count", 0),
                data.get("already_member_count", 0),
                len(data.get("skipped_deleted_ids", [])),
            )
        )


@run_companies_app.command("crm-count")
def run_companies_crm_count(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get count of companies added to CRM for a workflow."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_WORKFLOWS}/{workflow_id}/runs/companies/added-to-crm-count")

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(styled("Companies added to CRM: [bold]{}[/bold]", data.get("count", 0)))


@run_companies_app.command("delete")
def run_companies_delete(
    ctx: typer.Context,
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    company_ids: str = typer.Option(
        ..., "--company-ids", help="Comma-separated workflow company IDs"
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Delete workflow-discovered companies."""
    set_json_mode(json_output)
    ids_list = [i.strip() for i in company_ids.split(",") if i.strip()]
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete {len(ids_list)} workflow companies?", abort=True)

    # httpx delete() doesn't accept json body; use request() directly
    with get_api_client() as client:
        try:
            resp = client.request(
                "DELETE",
                f"{_WORKFLOWS}/{workflow_id}/runs/companies",
                json={"company_ids": ids_list},
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)
        except httpx.HTTPError as exc:
            _handle_connection_error(exc)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(styled("[green]Deleted {} workflow companies[/green]", data.get("deleted_count", 0)))

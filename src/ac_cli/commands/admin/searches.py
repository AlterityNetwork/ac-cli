"""Admin Sonar + Headhunter searches monitoring (super admin only)."""

from __future__ import annotations

import sys
from typing import Any

import typer

from ac_cli.commands._helpers import JSON_OPTION, _api_request, set_json_mode
from ac_cli.commands.admin import _ADMIN
from ac_cli.formatting import print_detail, print_json, print_table

searches_app = typer.Typer(help="Sonar + Headhunter searches monitoring")


_BASE = f"{_ADMIN}/searches"

# `--all` paginates with this size and refuses to walk past this many rows.
_BULK_PAGE_SIZE = 100
_BULK_MAX_ITEMS = 50_000


def _add_filters(
    params: dict[str, Any],
    *,
    start_date: str | None,
    end_date: str | None,
    source: str | None,
    org_ids: list[str] | None,
    user_ids: list[str] | None,
    status: str | None = None,
    q: str | None = None,
) -> None:
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if source:
        params["source"] = source
    if org_ids:
        params["organization_id"] = org_ids
    if user_ids:
        params["user_id"] = user_ids
    if status:
        params["status"] = status
    if q:
        params["q"] = q


def _walk_all(path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    """Page through `path` until exhausted or _BULK_MAX_ITEMS reached.

    Returns the merged list of items across pages.
    """
    page = 1
    out: list[dict[str, Any]] = []
    while True:
        page_params = dict(params)
        page_params["page"] = page
        page_params["page_size"] = _BULK_PAGE_SIZE
        resp = _api_request("get", path, params=page_params)
        data = resp.json()
        items = data.get("items") or []
        out.extend(items)
        if len(items) < _BULK_PAGE_SIZE:
            break
        if len(out) >= _BULK_MAX_ITEMS:
            print(
                f"warning: --all reached {_BULK_MAX_ITEMS} item cap; narrow your filters",
                file=sys.stderr,
            )
            break
        page += 1
    return out


@searches_app.command("summary")
def searches_summary(
    ctx: typer.Context,
    start_date: str | None = typer.Option(None, "--start-date", help="Start date (YYYY-MM-DD)"),
    end_date: str | None = typer.Option(None, "--end-date", help="End date (YYYY-MM-DD)"),
    source: str = typer.Option("both", "--source", help="sonar | headhunter | both"),
    org_id: list[str] | None = typer.Option(None, "--org-id", help="Filter by org ID (repeatable)"),
    user_id: list[str] | None = typer.Option(
        None, "--user-id", help="Filter by user ID (repeatable)"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Show search-activity summary across organizations."""
    set_json_mode(json_output)
    params: dict[str, Any] = {}
    _add_filters(
        params,
        start_date=start_date,
        end_date=end_date,
        source=source,
        org_ids=org_id,
        user_ids=user_id,
    )

    resp = _api_request("get", f"{_BASE}/summary", params=params)
    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(
        data,
        [
            ("total_runs", "Total Runs"),
            ("completed_runs", "Completed"),
            ("failed_runs", "Failed"),
            ("success_rate", "Success Rate %"),
            ("total_companies", "Total Companies"),
            ("total_people", "Total People"),
            ("avg_lead_score", "Avg Lead Score"),
            ("avg_relevance_score", "Avg Relevance Score"),
        ],
    )

    by_source = data.get("by_source") or {}
    for src in ("sonar", "headhunter"):
        bucket = by_source.get(src) or {}
        if not bucket:
            continue
        print_detail(
            bucket,
            [
                ("total_runs", f"{src.title()} Runs"),
                ("completed_runs", "  Completed"),
                ("failed_runs", "  Failed"),
                ("total_companies", "  Companies"),
                ("total_people", "  People"),
            ],
        )


@searches_app.command("runs")
def searches_runs(
    ctx: typer.Context,
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
    source: str = typer.Option("both", "--source"),
    org_id: list[str] | None = typer.Option(None, "--org-id"),
    user_id: list[str] | None = typer.Option(None, "--user-id"),
    status: str | None = typer.Option(
        None, "--status", help="pending | running | completed | failed"
    ),
    q: str | None = typer.Option(None, "-q", "--query"),
    page: int = typer.Option(1, "--page"),
    page_size: int = typer.Option(25, "--page-size"),
    all_: bool = typer.Option(False, "--all", help="Paginate through every page"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List search runs (Sonar + Headhunter) across organizations."""
    set_json_mode(json_output)
    params: dict[str, Any] = {}
    _add_filters(
        params,
        start_date=start_date,
        end_date=end_date,
        source=source,
        org_ids=org_id,
        user_ids=user_id,
        status=status,
        q=q,
    )

    if all_:
        items = _walk_all(f"{_BASE}/runs", params)
        # --all implies JSON output regardless of --json.
        print_json(items)
        return

    params["page"] = page
    params["page_size"] = page_size
    resp = _api_request("get", f"{_BASE}/runs", params=params)
    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data.get("items") or []
    print_table(
        items,
        [
            ("id", "Run ID"),
            ("source", "Source"),
            ("organization_id", "Org"),
            ("user_id", "User"),
            ("status", "Status"),
            ("started_at", "Started"),
            ("companies_count", "Companies"),
            ("people_count", "People"),
        ],
        title=f"Search Runs ({data.get('total_count', '?')} total)",
    )


@searches_app.command("run")
def searches_run(
    ctx: typer.Context,
    run_id: str = typer.Argument(..., help="Workflow run ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Show one search run (PII-scrubbed)."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_BASE}/runs/{run_id}")
    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(
        data,
        [
            ("id", "Run ID"),
            ("source", "Source"),
            ("organization_id", "Org"),
            ("user_id", "User"),
            ("status", "Status"),
            ("started_at", "Started"),
            ("completed_at", "Completed"),
            ("duration_ms", "Duration (ms)"),
            ("companies_count", "Companies"),
            ("people_count", "People"),
            ("error_message", "Error"),
        ],
    )


@searches_app.command("companies")
def searches_companies(
    ctx: typer.Context,
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
    source: str = typer.Option("both", "--source"),
    org_id: list[str] | None = typer.Option(None, "--org-id"),
    user_id: list[str] | None = typer.Option(None, "--user-id"),
    q: str | None = typer.Option(None, "-q", "--query"),
    page: int = typer.Option(1, "--page"),
    page_size: int = typer.Option(25, "--page-size"),
    all_: bool = typer.Option(False, "--all"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List companies discovered by Sonar/Headhunter runs."""
    set_json_mode(json_output)
    params: dict[str, Any] = {}
    _add_filters(
        params,
        start_date=start_date,
        end_date=end_date,
        source=source,
        org_ids=org_id,
        user_ids=user_id,
        q=q,
    )

    if all_:
        items = _walk_all(f"{_BASE}/companies", params)
        print_json(items)
        return

    params["page"] = page
    params["page_size"] = page_size
    resp = _api_request("get", f"{_BASE}/companies", params=params)
    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data.get("items") or []
    print_table(
        items,
        [
            ("name", "Name"),
            ("website", "Website"),
            ("source_workflow_type", "Source"),
            ("organization_id", "Org"),
            ("lead_score", "Lead"),
            ("country", "Country"),
            ("discovered_at", "Discovered"),
        ],
        title=f"Discovered Companies ({data.get('total_count', '?')} total)",
    )


@searches_app.command("people")
def searches_people(
    ctx: typer.Context,
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
    source: str = typer.Option("headhunter", "--source"),
    org_id: list[str] | None = typer.Option(None, "--org-id"),
    user_id: list[str] | None = typer.Option(None, "--user-id"),
    page: int = typer.Option(1, "--page"),
    page_size: int = typer.Option(25, "--page-size"),
    all_: bool = typer.Option(False, "--all"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List discovered people (de-identified — no names, emails, or LinkedIn)."""
    set_json_mode(json_output)
    params: dict[str, Any] = {}
    _add_filters(
        params,
        start_date=start_date,
        end_date=end_date,
        source=source,
        org_ids=org_id,
        user_ids=user_id,
    )

    if all_:
        items = _walk_all(f"{_BASE}/people", params)
        print_json(items)
        return

    params["page"] = page
    params["page_size"] = page_size
    resp = _api_request("get", f"{_BASE}/people", params=params)
    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data.get("items") or []
    print_table(
        items,
        [
            ("current_title", "Title"),
            ("current_company_text", "Company"),
            ("country", "Country"),
            ("relevance_score", "Relevance"),
            ("email_score", "Email Score"),
            ("organization_id", "Org"),
            ("discovered_at", "Discovered"),
        ],
        title=f"Discovered People ({data.get('total_count', '?')} total)",
    )

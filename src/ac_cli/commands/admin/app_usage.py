"""Admin app usage monitoring commands."""

from __future__ import annotations

import typer

from ac_cli.commands._helpers import JSON_OPTION, _api_request, set_json_mode
from ac_cli.commands.admin import _ADMIN
from ac_cli.formatting import print_detail, print_json, print_table

app_usage_app = typer.Typer(help="App usage monitoring")


@app_usage_app.command("summary")
def app_usage_summary(
    ctx: typer.Context,
    start_date: str | None = typer.Option(None, "--start-date", help="Start date (YYYY-MM-DD)"),
    end_date: str | None = typer.Option(None, "--end-date", help="End date (YYYY-MM-DD)"),
    org_id: str | None = typer.Option(None, "--org-id", help="Filter by organization ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Show app usage summary."""
    set_json_mode(json_output)
    params: dict = {}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if org_id:
        params["org_id"] = org_id

    resp = _api_request("get", f"{_ADMIN}/app-usage/summary", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(
        data,
        [
            ("total_opens", "Total Opens"),
            ("total_runs", "Total Runs"),
            ("total_events", "Total Events"),
            ("unique_users", "Unique Users"),
        ],
    )


@app_usage_app.command("users")
def app_usage_users(
    ctx: typer.Context,
    start_date: str | None = typer.Option(None, "--start-date", help="Start date (YYYY-MM-DD)"),
    end_date: str | None = typer.Option(None, "--end-date", help="End date (YYYY-MM-DD)"),
    sort: str | None = typer.Option(None, help="Sort field"),
    order: str | None = typer.Option(None, help="Sort order (asc/desc)"),
    page: int = typer.Option(1, help="Page number"),
    page_size: int = typer.Option(50, "--page-size", help="Page size"),
    search: str | None = typer.Option(None, help="Search query"),
    org_id: str | None = typer.Option(None, "--org-id", help="Filter by organization ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List app usage by user."""
    set_json_mode(json_output)
    params: dict = {"page": page, "page_size": page_size}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if sort:
        params["sort"] = sort
    if order:
        params["order"] = order
    if search:
        params["search"] = search
    if org_id:
        params["org_id"] = org_id

    resp = _api_request("get", f"{_ADMIN}/app-usage/users", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_table(
        data.get("items", []),
        [
            ("email", "Email"),
            ("full_name", "Name"),
            ("total_opens", "Opens"),
            ("total_runs", "Runs"),
            ("total_events", "Events"),
            ("last_active", "Last Active"),
        ],
        title=f"App Usage by User ({data.get('total', '?')} total)",
    )


@app_usage_app.command("user")
def app_usage_user(
    ctx: typer.Context,
    user_id: str = typer.Argument(..., help="User ID"),
    start_date: str | None = typer.Option(None, "--start-date", help="Start date (YYYY-MM-DD)"),
    end_date: str | None = typer.Option(None, "--end-date", help="End date (YYYY-MM-DD)"),
    org_id: str | None = typer.Option(None, "--org-id", help="Filter by organization ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get app usage details for a specific user."""
    set_json_mode(json_output)
    params: dict = {}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if org_id:
        params["org_id"] = org_id

    resp = _api_request("get", f"{_ADMIN}/app-usage/users/{user_id}", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(
        data,
        [
            ("email", "Email"),
            ("full_name", "Name"),
            ("total_opens", "Total Opens"),
            ("total_runs", "Total Runs"),
            ("total_events", "Total Events"),
        ],
    )

    by_app = data.get("by_app", [])
    if by_app:
        print_table(
            by_app,
            [
                ("app_name", "App"),
                ("opens", "Opens"),
                ("runs", "Runs"),
                ("events", "Events"),
            ],
            title="Usage by App",
        )

    recent_events = data.get("recent_events", [])
    if recent_events:
        print_table(
            recent_events,
            [
                ("event_type", "Event"),
                ("app_name", "App"),
                ("created_at", "Time"),
            ],
            title="Recent Events",
        )

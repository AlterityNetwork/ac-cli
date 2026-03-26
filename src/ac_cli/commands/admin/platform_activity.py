"""Admin platform activity monitoring commands."""

from __future__ import annotations

import typer

from ac_cli.commands._helpers import _api_request, JSON_OPTION, set_json_mode
from ac_cli.commands.admin import _ADMIN
from ac_cli.formatting import print_detail, print_json, print_table

platform_activity_app = typer.Typer(help="Platform activity monitoring")


@platform_activity_app.command("summary")
def platform_activity_summary(
    ctx: typer.Context,
    start_date: str | None = typer.Option(None, "--start-date", help="Start date (YYYY-MM-DD)"),
    end_date: str | None = typer.Option(None, "--end-date", help="End date (YYYY-MM-DD)"),
    org_id: str | None = typer.Option(None, "--org-id", help="Filter by organization ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Show platform activity summary."""
    set_json_mode(json_output)
    params: dict = {}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if org_id:
        params["org_id"] = org_id

    resp = _api_request("get", f"{_ADMIN}/platform-activity/summary", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(data, [
        ("total_events", "Total Events"),
        ("unique_users", "Unique Users"),
    ])

    by_category = data.get("by_category", [])
    if by_category:
        print_table(
            by_category,
            [
                ("category", "Category"),
                ("event_count", "Event Count"),
            ],
            title="Activity by Category",
        )


@platform_activity_app.command("users")
def platform_activity_users(
    ctx: typer.Context,
    start_date: str | None = typer.Option(None, "--start-date", help="Start date (YYYY-MM-DD)"),
    end_date: str | None = typer.Option(None, "--end-date", help="End date (YYYY-MM-DD)"),
    sort: str | None = typer.Option(None, help="Sort field"),
    order: str | None = typer.Option(None, help="Sort order (asc/desc)"),
    page: int = typer.Option(1, help="Page number"),
    page_size: int = typer.Option(50, "--page-size", help="Page size"),
    query: str | None = typer.Option(None, help="Search query"),
    org_id: str | None = typer.Option(None, "--org-id", help="Filter by organization ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List platform activity by user."""
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
    if query:
        params["query"] = query
    if org_id:
        params["org_id"] = org_id

    resp = _api_request("get", f"{_ADMIN}/platform-activity/users", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_table(
        data.get("items", []),
        [
            ("email", "Email"),
            ("full_name", "Name"),
            ("total_events", "Total Events"),
            ("last_active", "Last Active"),
        ],
        title=f"Platform Activity by User ({data.get('total', '?')} total)",
    )


@platform_activity_app.command("user")
def platform_activity_user(
    ctx: typer.Context,
    user_id: str = typer.Argument(..., help="User ID"),
    start_date: str | None = typer.Option(None, "--start-date", help="Start date (YYYY-MM-DD)"),
    end_date: str | None = typer.Option(None, "--end-date", help="End date (YYYY-MM-DD)"),
    org_id: str | None = typer.Option(None, "--org-id", help="Filter by organization ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get platform activity details for a specific user."""
    set_json_mode(json_output)
    params: dict = {}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if org_id:
        params["org_id"] = org_id

    resp = _api_request("get", f"{_ADMIN}/platform-activity/users/{user_id}", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(data, [
        ("email", "Email"),
        ("full_name", "Name"),
        ("total_events", "Total Events"),
    ])

    recent_events = data.get("recent_events", [])
    if recent_events:
        print_table(
            recent_events,
            [
                ("event_type", "Event Type"),
                ("category", "Category"),
                ("created_at", "Created At"),
            ],
            title="Recent Events",
        )

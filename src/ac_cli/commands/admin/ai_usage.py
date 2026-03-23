"""Admin AI usage monitoring commands."""

from __future__ import annotations

import typer

from ac_cli.commands._helpers import _api_request
from ac_cli.commands.admin import _ADMIN
from ac_cli.formatting import print_detail, print_json, print_table

ai_usage_app = typer.Typer(help="AI usage monitoring")


@ai_usage_app.command("summary")
def ai_usage_summary(
    ctx: typer.Context,
    start_date: str | None = typer.Option(None, "--start-date", help="Start date (YYYY-MM-DD)"),
    end_date: str | None = typer.Option(None, "--end-date", help="End date (YYYY-MM-DD)"),
    org_id: str | None = typer.Option(None, "--org-id", help="Filter by organization ID"),
) -> None:
    """Show AI usage summary."""
    params: dict = {}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if org_id:
        params["org_id"] = org_id

    resp = _api_request("get", f"{_ADMIN}/ai-usage/summary", params=params)

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
        return

    print_detail(data, [
        ("total_requests", "Total Requests"),
        ("total_tokens", "Total Tokens"),
        ("total_cost", "Total Cost"),
    ])

    by_model = data.get("by_model", [])
    if by_model:
        print_table(
            by_model,
            [
                ("model_id", "Model"),
                ("provider", "Provider"),
                ("requests", "Requests"),
                ("tokens", "Tokens"),
                ("cost", "Cost"),
            ],
            title="Usage by Model",
        )


@ai_usage_app.command("users")
def ai_usage_users(
    ctx: typer.Context,
    start_date: str | None = typer.Option(None, "--start-date", help="Start date (YYYY-MM-DD)"),
    end_date: str | None = typer.Option(None, "--end-date", help="End date (YYYY-MM-DD)"),
    sort: str | None = typer.Option(None, help="Sort field"),
    order: str | None = typer.Option(None, help="Sort order (asc/desc)"),
    page: int = typer.Option(1, help="Page number"),
    page_size: int = typer.Option(50, "--page-size", help="Page size"),
    search: str | None = typer.Option(None, help="Search query"),
    org_id: str | None = typer.Option(None, "--org-id", help="Filter by organization ID"),
) -> None:
    """List AI usage by user."""
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

    resp = _api_request("get", f"{_ADMIN}/ai-usage/users", params=params)

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
        return

    print_table(
        data.get("items", []),
        [
            ("email", "Email"),
            ("full_name", "Name"),
            ("total_cost", "Cost"),
            ("total_tokens", "Tokens"),
            ("total_requests", "Requests"),
            ("last_active", "Last Active"),
        ],
        title=f"AI Usage by User ({data.get('total', '?')} total)",
    )


@ai_usage_app.command("user")
def ai_usage_user(
    ctx: typer.Context,
    user_id: str = typer.Argument(..., help="User ID"),
    start_date: str | None = typer.Option(None, "--start-date", help="Start date (YYYY-MM-DD)"),
    end_date: str | None = typer.Option(None, "--end-date", help="End date (YYYY-MM-DD)"),
    org_id: str | None = typer.Option(None, "--org-id", help="Filter by organization ID"),
) -> None:
    """Get AI usage details for a specific user."""
    params: dict = {}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if org_id:
        params["org_id"] = org_id

    resp = _api_request("get", f"{_ADMIN}/ai-usage/users/{user_id}", params=params)

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
        return

    print_detail(data, [
        ("email", "Email"),
        ("full_name", "Name"),
        ("total_cost", "Total Cost"),
        ("total_tokens", "Total Tokens"),
        ("total_requests", "Total Requests"),
    ])

    by_model = data.get("by_model", [])
    if by_model:
        print_table(
            by_model,
            [
                ("model_id", "Model"),
                ("provider", "Provider"),
                ("requests", "Requests"),
                ("tokens", "Tokens"),
                ("cost", "Cost"),
            ],
            title="Usage by Model",
        )

    by_workflow = data.get("by_workflow", [])
    if by_workflow:
        print_table(
            by_workflow,
            [
                ("workflow_id", "Workflow"),
                ("requests", "Requests"),
                ("tokens", "Tokens"),
                ("cost", "Cost"),
            ],
            title="Usage by Workflow",
        )


@ai_usage_app.command("by-model")
def ai_usage_by_model(
    ctx: typer.Context,
    start_date: str | None = typer.Option(None, "--start-date", help="Start date (YYYY-MM-DD)"),
    end_date: str | None = typer.Option(None, "--end-date", help="End date (YYYY-MM-DD)"),
    org_id: str | None = typer.Option(None, "--org-id", help="Filter by organization ID"),
) -> None:
    """Show AI usage breakdown by model."""
    params: dict = {}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if org_id:
        params["org_id"] = org_id

    resp = _api_request("get", f"{_ADMIN}/ai-usage/by-model", params=params)

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("items", [])
    print_table(
        items,
        [
            ("model_id", "Model"),
            ("provider", "Provider"),
            ("requests", "Requests"),
            ("tokens", "Tokens"),
            ("cost", "Cost"),
        ],
        title="AI Usage by Model",
    )


@ai_usage_app.command("by-workflow")
def ai_usage_by_workflow(
    ctx: typer.Context,
    start_date: str | None = typer.Option(None, "--start-date", help="Start date (YYYY-MM-DD)"),
    end_date: str | None = typer.Option(None, "--end-date", help="End date (YYYY-MM-DD)"),
    org_id: str | None = typer.Option(None, "--org-id", help="Filter by organization ID"),
) -> None:
    """Show AI usage breakdown by workflow."""
    params: dict = {}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if org_id:
        params["org_id"] = org_id

    resp = _api_request("get", f"{_ADMIN}/ai-usage/by-workflow", params=params)

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("items", [])
    print_table(
        items,
        [
            ("workflow_id", "Workflow"),
            ("requests", "Requests"),
            ("tokens", "Tokens"),
            ("cost", "Cost"),
        ],
        title="AI Usage by Workflow",
    )


@ai_usage_app.command("details")
def ai_usage_details(
    ctx: typer.Context,
    start_date: str | None = typer.Option(None, "--start-date", help="Start date (YYYY-MM-DD)"),
    end_date: str | None = typer.Option(None, "--end-date", help="End date (YYYY-MM-DD)"),
    limit: int = typer.Option(50, help="Max results"),
    offset: int = typer.Option(0, help="Offset"),
    org_id: str | None = typer.Option(None, "--org-id", help="Filter by organization ID"),
    model_id: str | None = typer.Option(None, "--model-id", help="Filter by model ID"),
    user_id: str | None = typer.Option(None, "--user-id", help="Filter by user ID"),
    workflow_run_id: str | None = typer.Option(None, "--workflow-run-id", help="Filter by workflow run ID"),
) -> None:
    """List detailed AI usage records."""
    params: dict = {"limit": limit, "offset": offset}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if org_id:
        params["org_id"] = org_id
    if model_id:
        params["model_id"] = model_id
    if user_id:
        params["user_id"] = user_id
    if workflow_run_id:
        params["workflow_run_id"] = workflow_run_id

    resp = _api_request("get", f"{_ADMIN}/ai-usage/details", params=params)

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("items", [])
    print_table(
        items,
        [
            ("id", "ID"),
            ("model_id", "Model"),
            ("user_email", "User"),
            ("workflow_id", "Workflow"),
            ("tokens", "Tokens"),
            ("cost", "Cost"),
            ("created_at", "Created"),
        ],
        title=f"AI Usage Details ({len(items)} records)",
    )

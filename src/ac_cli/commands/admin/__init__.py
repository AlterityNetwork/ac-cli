"""Admin commands: users, organizations, queues, demo."""

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    _build_body,  # noqa: F401
    _handle_error,  # noqa: F401
    set_json_mode,
)
from ac_cli.formatting import print_json

app = typer.Typer(help="Admin commands (super admin only)")

_ADMIN = "/api/v1/admin"


@app.callback()
def admin_callback(ctx: typer.Context) -> None:
    ctx.ensure_object(dict)


# -- Standalone commands ------------------------------------------------------


@app.command("analytics-overview")
def analytics_overview(
    ctx: typer.Context,
    start_date: str | None = typer.Option(None, "--start-date", help="Start date (YYYY-MM-DD)"),
    end_date: str | None = typer.Option(None, "--end-date", help="End date (YYYY-MM-DD)"),
    organization_id: str | None = typer.Option(None, "--org-id", help="Filter by organization ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Show admin analytics overview summary."""
    set_json_mode(json_output)
    params: dict = {}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if organization_id:
        params["organization_id"] = organization_id

    resp = _api_request("get", f"{_ADMIN}/analytics-overview/summary", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    rprint("\n[bold]Analytics Overview[/bold]\n")
    rprint("[bold]Daily Averages[/bold]")
    rprint(f"  AI requests/day: {data.get('ai_requests_per_day', 0):.1f}")
    rprint(f"  App runs/day: {data.get('app_runs_per_day', 0):.1f}")
    rprint(f"  Platform events/day: {data.get('platform_events_per_day', 0):.1f}")
    rprint(f"\n[bold]Active Users[/bold]")
    rprint(f"  Active user rate: {data.get('active_user_rate', 0):.1f}%")
    rprint(f"  Total active: {data.get('total_active_users', 0)}")
    rprint(f"  Total org members: {data.get('total_org_members', 0)}")
    rprint(f"\n[bold]AI Usage[/bold]")
    rprint(f"  Total cost: ${data.get('ai_total_cost', 0):.2f}")
    change_cost = data.get("ai_change_cost")
    if change_cost is not None:
        rprint(f"  Cost change: {change_cost:+.1f}%")
    rprint(f"\n[bold]App Usage[/bold]")
    rprint(f"  Total runs: {data.get('app_total_runs', 0)}")
    change_runs = data.get("app_change_runs")
    if change_runs is not None:
        rprint(f"  Runs change: {change_runs:+.1f}%")
    rprint(f"\n[bold]Platform Activity[/bold]")
    rprint(f"  Total events: {data.get('platform_total_events', 0)}")
    change_events = data.get("platform_change_events")
    if change_events is not None:
        rprint(f"  Events change: {change_events:+.1f}%")


@app.command("cache-stats")
def cache_stats(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """Show application cache hit/miss statistics."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_ADMIN}/debug/cache-stats")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    rprint("\n[bold]Cache Statistics[/bold]\n")
    for key, value in data.items():
        rprint(f"  {key}: {value}")


# -- Register sub-command groups from submodules ------------------------------

from ac_cli.commands.admin.users import users_app  # noqa: E402
from ac_cli.commands.admin.organizations import organizations_app  # noqa: E402
from ac_cli.commands.admin.queues import queues_app  # noqa: E402
from ac_cli.commands.admin.demo import demo_app  # noqa: E402
from ac_cli.commands.admin.onboarding import onboarding_app  # noqa: E402
from ac_cli.commands.admin.app_usage import app_usage_app  # noqa: E402
from ac_cli.commands.admin.ai_usage import ai_usage_app  # noqa: E402
from ac_cli.commands.admin.platform_activity import platform_activity_app  # noqa: E402
from ac_cli.commands.admin.legal_documents import legal_docs_app  # noqa: E402
from ac_cli.commands.admin.admin_resources import admin_resources_app  # noqa: E402
from ac_cli.commands.admin.admin_apps import admin_apps_app  # noqa: E402
from ac_cli.commands.admin.searches import searches_app  # noqa: E402

app.add_typer(users_app, name="users")
app.add_typer(organizations_app, name="orgs")
app.add_typer(queues_app, name="queues")
app.add_typer(demo_app, name="demo")
app.add_typer(onboarding_app, name="onboarding")
app.add_typer(app_usage_app, name="app-usage")
app.add_typer(ai_usage_app, name="ai-usage")
app.add_typer(platform_activity_app, name="platform-activity")
app.add_typer(legal_docs_app, name="legal-docs")
app.add_typer(admin_resources_app, name="resources")
app.add_typer(admin_apps_app, name="apps")
app.add_typer(searches_app, name="searches")

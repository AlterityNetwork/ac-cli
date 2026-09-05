"""Customer-facing organization analytics commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import JSON_OPTION, _api_request, set_json_mode
from ac_cli.formatting import as_text, print_json, print_table, styled

app = typer.Typer(help="Customer-facing org analytics")

_ANALYTICS = "/api/v1/analytics"

# (response key, display label) for the MetricDelta KPI rows, in display order.
_DELTA_METRICS = [
    ("sonar_companies", "Sonar companies"),
    ("sonar_signals", "Sonar signals"),
    ("sonar_searches", "Sonar searches"),
    ("headhunter_people", "Headhunter people"),
    ("headhunter_searches", "Headhunter searches"),
    ("sequences_launched", "Sequences launched"),
    ("emails_sent", "Emails sent"),
    ("email_replies", "Email replies"),
    ("companies_new", "New companies"),
    ("people", "New people"),
    ("tasks_created", "Tasks created"),
    ("tasks_completed", "Tasks completed"),
    ("workflow_runs", "Workflow runs"),
    ("logins", "Logins"),
    ("active_users", "Active users"),
]


@app.callback()
def analytics_callback(ctx: typer.Context) -> None:
    ctx.ensure_object(dict)


@app.command("overview")
def analytics_overview(
    ctx: typer.Context,
    period_days: int = typer.Option(
        30,
        "--period-days",
        min=1,
        max=365,
        help="Period in days (1-365)",
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Show the org's activity and output overview for a period."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_ANALYTICS}/overview", params={"period_days": period_days})

    data = resp.json()
    if json_output:
        print_json(data)
        return

    rprint(
        styled(
            "[bold]Org analytics[/bold] {} to {} ({} days)",
            data.get("start_date"),
            data.get("end_date"),
            data.get("period_days"),
        )
    )
    rows = []
    for key, label in _DELTA_METRICS:
        delta = data.get(key) or {}
        # change_pct is null when the previous period was zero: growth from
        # nothing has no percentage. The key is present, so `.get(..., 0.0)`
        # hands back None and f"{None:+.1f}%" raises TypeError.
        change = delta.get("change_pct")
        rows.append(
            {
                "metric": label,
                "current": delta.get("current", 0),
                "previous": delta.get("previous", 0),
                "change": "-" if change is None else f"{change:+.1f}%",
            }
        )
    print_table(
        rows,
        [
            ("metric", "Metric"),
            ("current", "Current"),
            ("previous", "Previous"),
            ("change", "Change"),
        ],
        title="Period metrics",
    )
    rprint(as_text(f"  Reply rate: {data.get('reply_rate', 0.0):.1f}%"))
    rprint(as_text(f"  Task completion rate: {data.get('task_completion_rate', 0.0):.1f}%"))
    rprint(as_text(f"  Active sequences: {data.get('sequences_active', 0)}"))
    rprint(as_text(f"  Companies total: {data.get('companies_total', 0)}"))
    rprint(as_text(f"  People total: {data.get('people_total', 0)}"))

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
    ("prospects_found", "Prospects found"),
    ("prospects_watched", "Prospects watched"),
    ("prospects_dismissed", "Prospects dismissed"),
    ("prospects_pursued", "Prospects pursued"),
    ("signals_searches", "Signals searches"),
    ("sequence_prospects_added", "Prospects added to sequences"),
    ("outbound_touches", "Outbound touches"),
    ("replies", "Replies"),
    ("sequence_emails_sent", "Sequence emails sent"),
    ("companies_new", "New companies"),
    ("people", "New people"),
    ("tasks_created", "Tasks created"),
    ("tasks_completed", "Tasks completed"),
    ("workflow_runs", "Workflow runs"),
    ("logins", "Logins"),
    ("active_users", "Active users"),
]


def _rate_text(value: float | None, suffix: str) -> str:
    """Format a rate or an average, or a dash when the period has none."""
    return "-" if value is None else f"{value:.1f}{suffix}"


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
    rprint(as_text(f"  Watching now: {data.get('prospects_watching_total', 0)}"))
    searches = (data.get("signals_searches") or {}).get("current", 0)
    saved = data.get("signals_searches_saved", 0)
    saved_share = f" ({saved / searches * 100:.1f}%)" if searches else ""
    rprint(as_text(f"  Saved searches: {saved} of {searches}{saved_share}"))
    pursued = _rate_text((data.get("prospects_pursued_rate") or {}).get("current"), "%")
    found_note = " of the prospects found" if pursued != "-" else ""
    rprint(as_text(f"  Prospects pursued: {pursued}{found_note}"))
    reply = _rate_text((data.get("avg_reply_hours") or {}).get("current"), " hours")
    rprint(as_text(f"  Average time to reply: {reply}"))
    for key, label in (
        ("email_reply_rate", "Email reply rate"),
        ("email_positive_reply_rate", "Positive reply rate"),
        ("email_bounce_rate", "Bounce rate"),
    ):
        rate = _rate_text((data.get(key) or {}).get("current"), "%")
        rprint(as_text(f"  {label}: {rate}"))
    rprint(as_text(f"  Live sequences: {data.get('sequences_active', 0)}"))
    rprint(as_text(f"  Task completion rate: {data.get('task_completion_rate', 0.0):.1f}%"))
    rprint(as_text(f"  Companies total: {data.get('companies_total', 0)}"))
    rprint(as_text(f"  People total: {data.get('people_total', 0)}"))

    ranking = data.get("sequences_by_reply_rate") or []
    if ranking:
        print_table(
            [
                {
                    "name": row.get("name", ""),
                    "status": row.get("status", ""),
                    "prospects": row.get("prospects", 0),
                    "replies": row.get("replies", 0),
                    "reply_rate": f"{row.get('reply_rate') or 0.0:.1f}%",
                }
                for row in ranking
            ],
            [
                ("name", "Sequence"),
                ("status", "Status"),
                ("prospects", "Prospects"),
                ("replies", "Replies"),
                ("reply_rate", "Reply rate"),
            ],
            title="Sequences by reply rate (all time)",
        )

"""Customer-facing organization analytics commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import JSON_OPTION, _api_request, refuse_local, set_json_mode
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
    ("linkedin_requests_sent", "LinkedIn requests sent"),
    ("linkedin_requests_accepted", "LinkedIn requests accepted"),
    ("linkedin_requests_awaiting", "LinkedIn requests awaiting acceptance"),
    ("companies_new", "New companies"),
    ("people", "New people"),
    ("tasks_created", "Tasks created"),
    ("tasks_completed", "Tasks completed"),
    ("workflow_runs", "Workflow runs"),
    ("logins", "Logins"),
    ("active_users", "Active users"),
]


# (category key, display label) in the order of the analytics page.
_CATEGORIES = [
    ("interested", "Interested"),
    ("referral", "Referral"),
    ("out_of_office", "Out of office"),
    ("unclear", "Unclear"),
    ("not_interested", "Not interested"),
    ("opted_out", "Opted out"),
    ("no_response", "No response"),
]
_CATEGORY_LABELS = dict(_CATEGORIES)
_SCOPES = ("replies", "touches")
_CHANNELS = {"email": "Email", "linkedin": "LinkedIn"}
_REPLIES_LIMIT = 500


def _one_of(name: str, value: str | None, allowed: tuple[str, ...]) -> None:
    if value is not None and value not in allowed:
        refuse_local(f"{name} must be one of {', '.join(allowed)}", value)


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
        ("linkedin_acceptance_rate", "LinkedIn acceptance rate"),
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


def _time_text(value: str | None) -> str:
    """Format an ISO time as date, hours and minutes, or a dash."""
    return value[:16].replace("T", " ") if value else "-"


def _reply_rows(items: list[dict]) -> list[dict]:
    return [
        {
            "person": item.get("person_name") or "-",
            "company": item.get("company_name") or "-",
            "channel": _CHANNELS.get(item.get("channel") or "", "-"),
            "category": _CATEGORY_LABELS.get(item.get("category") or "", "-"),
            "excerpt": item.get("excerpt") or "-",
            "time": _time_text(item.get("replied_at")),
        }
        for item in items
    ]


_REPLY_COLUMNS = [
    ("person", "Person"),
    ("company", "Company"),
    ("channel", "Channel"),
    ("category", "Category"),
    ("excerpt", "Excerpt"),
    ("time", "Time"),
]


@app.command("replies")
def analytics_replies(
    ctx: typer.Context,
    period_days: int = typer.Option(30, "--period-days", help="Period in days (1-365)"),
    scope: str = typer.Option(
        "replies",
        help="replies: the prospects behind the Replies tile. touches: the prospects "
        "touched on --channel in the period, by their reply",
    ),
    channel: str | None = typer.Option(None, help="email or linkedin. Needed for --scope touches"),
    category: str | None = typer.Option(
        None,
        help="Only list this category: interested, referral, out_of_office, unclear, "
        "not_interested, opted_out or no_response",
    ),
    limit: int | None = typer.Option(None, help="Most prospects to list (1-500)"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Show the replies of a period by category, with each reply."""
    set_json_mode(json_output)
    if not 1 <= period_days <= 365:
        refuse_local("--period-days must be between 1 and 365", period_days)
    _one_of("--scope", scope, _SCOPES)
    _one_of("--channel", channel, tuple(_CHANNELS))
    _one_of("--category", category, tuple(_CATEGORY_LABELS))
    if limit is not None and not 1 <= limit <= _REPLIES_LIMIT:
        refuse_local(f"--limit must be between 1 and {_REPLIES_LIMIT}", limit)
    if scope == "touches" and channel is None:
        refuse_local("--scope touches needs --channel")

    params: dict[str, str | int] = {"period_days": period_days}
    if scope != "replies":
        params["scope"] = scope
    for key, value in (("channel", channel), ("category", category), ("limit", limit)):
        if value is not None:
            params[key] = value
    data = _api_request("get", f"{_ANALYTICS}/replies", params=params).json()
    if json_output:
        print_json(data)
        return

    touches = data.get("scope") == "touches"
    heading = "Prospects touched" if touches else "Replies"
    rprint(
        styled(
            "[bold]{}: {}[/bold]  {} to {} ({} days)",
            heading,
            data.get("total", 0),
            data.get("start_date"),
            data.get("end_date"),
            data.get("period_days"),
        )
    )
    counts = data.get("by_category") or {}
    print_table(
        [
            {"category": label, "count": counts.get(key, 0)}
            for key, label in _CATEGORIES
            if key in counts
        ],
        [("category", "Category"), ("count", "Prospects")],
    )
    items = data.get("items") or []
    if items:
        print_table(_reply_rows(items), _REPLY_COLUMNS, title=heading)
        if data.get("truncated"):
            rprint(as_text(f"  Showing {len(items)} of {data.get('items_total', 0)}"))
    else:
        rprint(as_text("  No replies in this period"))

    autos = data.get("auto_replies") or []
    rprint(
        as_text(f"  Automatic replies: {data.get('auto_reply_count', 0)} (not counted in Replies)")
    )
    if autos:
        print_table(_reply_rows(autos), _REPLY_COLUMNS)
    bounced = data.get("bounced") or []
    rprint(
        as_text(
            f"  Bounced: {data.get('bounced_count', 0)} prospects, "
            f"{data.get('bounced_emails', 0)} emails (not counted in Replies)"
        )
    )
    if bounced:
        print_table(
            [
                {
                    "person": row.get("person_name") or "-",
                    "company": row.get("company_name") or "-",
                    "email": row.get("email") or "-",
                    "emails": row.get("emails", 0),
                    "time": _time_text(row.get("bounced_at")),
                }
                for row in bounced
            ],
            [
                ("person", "Person"),
                ("company", "Company"),
                ("email", "Email"),
                ("emails", "Bounces"),
                ("time", "Time"),
            ],
        )

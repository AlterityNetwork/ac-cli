"""Envoy sales signals commands.

`signals` is a sub-app with two forms:

- ``ac envoy signals for <recipient-id>`` — per-recipient signals (LinkedIn,
  news, funding, hiring, etc.).
- ``ac envoy signals recent [--since-days N] [--limit N]`` — cross-company
  list of signals discovered within a rolling window. Powers the agent's
  "what's been discovered in the last 7 days" path and the Launchpad
  hottest-signals view.
"""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import JSON_OPTION, _api_request, set_json_mode
from ac_cli.commands.envoy import _ENVOY
from ac_cli.formatting import print_json, print_table

signals_app = typer.Typer(help="Sales signals (per recipient or recent across org)")


@signals_app.callback()
def signals_callback(ctx: typer.Context) -> None:
    ctx.ensure_object(dict)


@signals_app.command("for")
def signals_for(
    ctx: typer.Context,
    recipient_id: str = typer.Argument(..., help="Recipient ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get sales signals for a specific recipient."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_ENVOY}/recipients/{recipient_id}/sales-signals")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("data", [])
    if not items:
        rprint("[dim]No signals found.[/dim]")
        return

    print_table(
        items,
        [
            ("signal_type", "Type"),
            ("title", "Title"),
            ("snippet", "Snippet"),
            ("date", "Date"),
        ],
        title=f"Sales Signals ({len(items)})",
    )


@signals_app.command("recent")
def signals_recent(
    ctx: typer.Context,
    since_days: int = typer.Option(
        7,
        "--since-days",
        help="Window in days (default 7, clamped server-side to 1-365).",
    ),
    limit: int = typer.Option(
        20,
        "--limit",
        help="Max number of signals to return (clamped server-side to 1-200).",
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """List recent signals across all companies in the org."""
    set_json_mode(json_output)
    params: dict = {"since_days": since_days, "limit": limit}
    resp = _api_request("get", f"{_ENVOY}/signals/recent", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("data", [])
    if not items:
        rprint(f"[dim]No signals in the last {since_days} days.[/dim]")
        return

    # Flatten for the table — the response nests the underlying SalesSignal
    # under `signal` to keep company metadata at the top level.
    rows = [
        {
            "company_name": row.get("company_name") or "",
            "signal_type": (row.get("signal") or {}).get("signal_type", ""),
            "title": (row.get("signal") or {}).get("title", ""),
            "date": (row.get("signal") or {}).get("date", ""),
        }
        for row in items
    ]
    print_table(
        rows,
        [
            ("company_name", "Company"),
            ("signal_type", "Type"),
            ("title", "Title"),
            ("date", "Date"),
        ],
        title=f"Recent Signals ({len(items)}, last {since_days}d)",
    )

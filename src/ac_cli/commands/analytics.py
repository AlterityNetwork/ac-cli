"""Customer-facing organization analytics commands."""

from typing import Any

import typer
from rich import print as rprint

from ac_cli.commands._helpers import JSON_OPTION, _api_request, set_json_mode
from ac_cli.formatting import print_json

app = typer.Typer(help="Organization analytics")
_ANALYTICS = "/api/v1/analytics"


def _current(data: dict[str, Any], key: str) -> int:
    metric = data.get(key)
    return int(metric.get("current", 0)) if isinstance(metric, dict) else 0


@app.command("overview")
def overview(
    ctx: typer.Context,
    period_days: int = typer.Option(
        30,
        "--period-days",
        min=1,
        max=365,
        help="Reporting window in days",
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Show the active organization's cross-product analytics overview."""
    set_json_mode(json_output)
    response = _api_request(
        "get",
        f"{_ANALYTICS}/overview",
        params={"period_days": period_days},
    )
    data = response.json()
    if json_output:
        print_json(data)
        return

    rprint(f"\n[bold]Organization Analytics ({data.get('period_days', period_days)} days)[/bold]\n")
    rprint(f"  Companies discovered: {_current(data, 'sonar_companies')}")
    rprint(f"  Signals found: {_current(data, 'sonar_signals')}")
    rprint(f"  People found: {_current(data, 'headhunter_people')}")
    rprint(f"  Emails sent: {_current(data, 'emails_sent')}")
    rprint(f"  CRM companies added: {_current(data, 'companies_new')}")

"""Admin credit-prices commands: the platform price book (super admin).

A price row is never changed in place. A new price for an action key is a new
version of that key, and the API gives it the next version number.
"""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    _build_body,
    set_json_mode,
)
from ac_cli.commands.admin import _ADMIN
from ac_cli.formatting import print_json, print_table, styled

credit_prices_app = typer.Typer(help="Credit price book: price per action and unit (super admin)")

_UNITS = "run, row, company, entity, thousand_tokens, draft, message or call"


@credit_prices_app.command("list")
def credit_prices_list(
    ctx: typer.Context,
    action_key: str | None = typer.Option(None, "--action-key", help="Show one action key"),
    all_versions: bool = typer.Option(
        False, "--all-versions", help="Show every version, not only the latest per key"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """List the credit prices, the latest version of each action key by default."""
    set_json_mode(json_output)
    params: dict = {"latest_only": "false" if all_versions else "true"}
    if action_key:
        params["action_key"] = action_key
    resp = _api_request("get", f"{_ADMIN}/credit-prices", params=params)
    data = resp.json()
    if json_output:
        print_json(data)
        return
    if not data:
        rprint("[yellow]No credit prices found.[/yellow]")
        return
    print_table(
        data,
        [
            ("action_key", "Action"),
            ("unit", "Unit"),
            ("credits", "Credits"),
            ("minimum_credits", "Minimum"),
            ("version", "Version"),
            ("effective_from", "Effective from"),
        ],
        title=f"Credit Prices ({len(data)})",
    )


def _usd(value: float | None) -> str:
    return "-" if value is None else f"${value:,.4f}"


@credit_prices_app.command("costs")
def credit_prices_costs(
    ctx: typer.Context,
    days: int = typer.Option(30, "--days", min=1, max=365, help="Days in the window that ends now"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Show what each action cost us in USD and what it charged in credits."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_ADMIN}/credit-prices/costs", params={"days": days})
    data = resp.json()
    if json_output:
        print_json(data)
        return
    actions = data.get("actions") or []
    if not actions:
        rprint(styled("[yellow]No metered actions in the last {} days.[/yellow]", data.get("days")))
        return
    rows = [
        {
            **action,
            "cost_usd": _usd(action.get("cost_usd")),
            "cost_per_unit_usd": _usd(action.get("cost_per_unit_usd")),
            "cost_per_credit_usd": _usd(action.get("cost_per_credit_usd")),
        }
        for action in actions
    ]
    print_table(
        rows,
        [
            ("action_key", "Action"),
            ("cost_usd", "Cost"),
            ("units", "Units"),
            ("credits", "Credits"),
            ("cost_per_unit_usd", "Per unit"),
            ("cost_per_credit_usd", "Per credit"),
        ],
        title=f"Action costs, last {data.get('days')} days",
    )


@credit_prices_app.command("create")
def credit_prices_create(
    ctx: typer.Context,
    action_key: str = typer.Option(
        ..., "--action-key", help="Action key, for example people.search"
    ),
    unit: str = typer.Option(..., help=f"What one charge counts: {_UNITS}"),
    credits: int = typer.Option(..., help="Credits per unit"),
    minimum_credits: int | None = typer.Option(
        None, "--minimum-credits", help="Smallest charge for one run; 0 sets no minimum"
    ),
    effective_from: str | None = typer.Option(
        None,
        "--effective-from",
        help=(
            "ISO 8601 instant with a timezone, at least a minute from now, "
            "for example 2026-12-01T00:00:00+00:00; defaults to a minute from now"
        ),
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Add a new price version for one action key."""
    set_json_mode(json_output)
    body = _build_body(
        action_key=action_key,
        unit=unit,
        credits=credits,
        minimum_credits=minimum_credits,
        effective_from=effective_from,
    )
    resp = _api_request("post", f"{_ADMIN}/credit-prices", json=body)
    data = resp.json()
    if json_output:
        print_json(data)
        return
    rprint(
        styled(
            "[green]Created {} version {}:[/green] {} credits per {}",
            data.get("action_key"),
            data.get("version"),
            data.get("credits"),
            data.get("unit"),
        )
    )

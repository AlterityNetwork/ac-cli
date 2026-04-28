"""Admin subscription-plans commands."""

from __future__ import annotations

import json as _json

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    _build_body,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.commands.admin import _ADMIN
from ac_cli.formatting import print_detail, print_json, print_table

subscription_plans_app = typer.Typer(help="Subscription plan catalog (super admin)")


def _features_from(features_json: str | None) -> dict | None:
    if features_json is None:
        return None
    try:
        parsed = _json.loads(features_json)
    except _json.JSONDecodeError as exc:
        rprint(f"[red]--features is not valid JSON: {exc}[/red]")
        raise typer.Exit(code=2)
    if not isinstance(parsed, dict):
        rprint("[red]--features must be a JSON object[/red]")
        raise typer.Exit(code=2)
    return parsed


@subscription_plans_app.command("list")
def plans_list(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """List subscription plans."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_ADMIN}/subscription-plans")
    data = resp.json()
    if json_output:
        print_json(data)
        return
    items = data if isinstance(data, list) else data.get("data", [])
    print_table(
        items,
        [
            ("slug", "Slug"),
            ("name", "Name"),
            ("monthly_price_cents", "Monthly ¢"),
            ("annual_price_cents", "Annual ¢"),
            ("is_active", "Active"),
            ("id", "ID"),
        ],
        title=f"Subscription Plans ({len(items)})",
    )


@subscription_plans_app.command("get")
def plans_get(
    ctx: typer.Context,
    plan_id: str = typer.Argument(..., help="Plan ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get a subscription plan by ID."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_ADMIN}/subscription-plans/{plan_id}")
    data = resp.json()
    if json_output:
        print_json(data)
        return
    print_detail(data, [
        ("id", "ID"),
        ("slug", "Slug"),
        ("name", "Name"),
        ("description", "Description"),
        ("monthly_price_cents", "Monthly ¢"),
        ("annual_price_cents", "Annual ¢"),
        ("is_active", "Active"),
        ("features", "Features"),
        ("created_at", "Created"),
        ("updated_at", "Updated"),
    ])


@subscription_plans_app.command("create")
def plans_create(
    ctx: typer.Context,
    slug: str = typer.Option(..., help="Plan slug"),
    name: str = typer.Option(..., help="Plan name"),
    monthly_price_cents: int = typer.Option(..., "--monthly-price-cents", help="Monthly price (cents)"),
    annual_price_cents: int = typer.Option(..., "--annual-price-cents", help="Annual price (cents)"),
    description: str | None = typer.Option(None, help="Description"),
    features: str | None = typer.Option(None, help="JSON object of feature flags"),
    is_active: bool | None = typer.Option(None, "--active/--inactive", help="Active state"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create a subscription plan."""
    set_json_mode(json_output)
    body = _build_body(
        slug=slug,
        name=name,
        description=description,
        monthly_price_cents=monthly_price_cents,
        annual_price_cents=annual_price_cents,
        features=_features_from(features),
        is_active=is_active,
    )
    resp = _api_request("post", f"{_ADMIN}/subscription-plans", json=body)
    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Created plan:[/green] {data.get('slug')} ({data.get('id')})")


@subscription_plans_app.command("update")
def plans_update(
    ctx: typer.Context,
    plan_id: str = typer.Argument(..., help="Plan ID"),
    slug: str | None = typer.Option(None, help="Plan slug"),
    name: str | None = typer.Option(None, help="Plan name"),
    description: str | None = typer.Option(None, help="Description"),
    monthly_price_cents: int | None = typer.Option(None, "--monthly-price-cents"),
    annual_price_cents: int | None = typer.Option(None, "--annual-price-cents"),
    features: str | None = typer.Option(None, help="JSON object of feature flags"),
    is_active: bool | None = typer.Option(None, "--active/--inactive"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update a subscription plan."""
    set_json_mode(json_output)
    body = _build_body(
        slug=slug,
        name=name,
        description=description,
        monthly_price_cents=monthly_price_cents,
        annual_price_cents=annual_price_cents,
        features=_features_from(features),
        is_active=is_active,
    )
    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)
    resp = _api_request("patch", f"{_ADMIN}/subscription-plans/{plan_id}", json=body)
    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Updated plan {plan_id}[/green]")


@subscription_plans_app.command("delete")
def plans_delete(
    plan_id: str = typer.Argument(..., help="Plan ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a subscription plan."""
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete plan {plan_id}?", abort=True)
    _api_request("delete", f"{_ADMIN}/subscription-plans/{plan_id}")
    rprint(f"[green]Deleted plan {plan_id}[/green]")

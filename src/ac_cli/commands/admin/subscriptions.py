"""Admin subscriptions commands."""

from __future__ import annotations

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

subscriptions_app = typer.Typer(help="Manage org subscriptions (super admin)")


@subscriptions_app.command("list")
def subscriptions_list(
    ctx: typer.Context,
    organization_id: str | None = typer.Option(None, "--org-id"),
    status: str | None = typer.Option(None),
    limit: int = typer.Option(50, help="Max results"),
    offset: int = typer.Option(0, help="Pagination offset"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List subscriptions across orgs."""
    set_json_mode(json_output)
    params: dict = {"limit": limit, "offset": offset}
    if organization_id:
        params["organization_id"] = organization_id
    if status:
        params["status"] = status
    resp = _api_request("get", f"{_ADMIN}/subscriptions", params=params)
    data = resp.json()
    if json_output:
        print_json(data)
        return
    items = data if isinstance(data, list) else data.get("data", [])
    print_table(
        items,
        [
            ("id", "ID"),
            ("organization_id", "Org"),
            ("plan_id", "Plan"),
            ("billing_period", "Billing"),
            ("status", "Status"),
            ("started_at", "Started"),
        ],
        title=f"Subscriptions ({data.get('total', len(items))} total)",
    )


@subscriptions_app.command("get")
def subscriptions_get(
    ctx: typer.Context,
    subscription_id: str = typer.Argument(..., help="Subscription ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get a subscription by ID."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_ADMIN}/subscriptions/{subscription_id}")
    data = resp.json()
    if json_output:
        print_json(data)
        return
    print_detail(data, [
        ("id", "ID"),
        ("organization_id", "Org"),
        ("plan_id", "Plan"),
        ("billing_period", "Billing"),
        ("status", "Status"),
        ("started_at", "Started"),
        ("ended_at", "Ended"),
        ("trial_ends_at", "Trial Ends"),
        ("stripe_customer_id", "Stripe Customer"),
        ("stripe_subscription_id", "Stripe Sub"),
    ])


@subscriptions_app.command("create")
def subscriptions_create(
    ctx: typer.Context,
    organization_id: str = typer.Option(..., "--org-id", help="Organization ID"),
    plan_id: str = typer.Option(..., "--plan-id", help="Plan ID"),
    billing_period: str = typer.Option(..., "--billing-period", help="monthly | annual"),
    started_at: str = typer.Option(..., "--started-at", help="ISO start date"),
    status: str | None = typer.Option(None),
    ended_at: str | None = typer.Option(None, "--ended-at"),
    trial_ends_at: str | None = typer.Option(None, "--trial-ends-at"),
    stripe_customer_id: str | None = typer.Option(None, "--stripe-customer-id"),
    stripe_subscription_id: str | None = typer.Option(None, "--stripe-subscription-id"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create a subscription."""
    set_json_mode(json_output)
    body = _build_body(
        organization_id=organization_id,
        plan_id=plan_id,
        billing_period=billing_period,
        started_at=started_at,
        status=status,
        ended_at=ended_at,
        trial_ends_at=trial_ends_at,
        stripe_customer_id=stripe_customer_id,
        stripe_subscription_id=stripe_subscription_id,
    )
    resp = _api_request("post", f"{_ADMIN}/subscriptions", json=body)
    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Created subscription {data.get('id')}[/green]")


@subscriptions_app.command("update")
def subscriptions_update(
    ctx: typer.Context,
    subscription_id: str = typer.Argument(..., help="Subscription ID"),
    plan_id: str | None = typer.Option(None, "--plan-id"),
    billing_period: str | None = typer.Option(None, "--billing-period"),
    status: str | None = typer.Option(None),
    started_at: str | None = typer.Option(None, "--started-at"),
    ended_at: str | None = typer.Option(None, "--ended-at"),
    trial_ends_at: str | None = typer.Option(None, "--trial-ends-at"),
    stripe_customer_id: str | None = typer.Option(None, "--stripe-customer-id"),
    stripe_subscription_id: str | None = typer.Option(None, "--stripe-subscription-id"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update a subscription."""
    set_json_mode(json_output)
    body = _build_body(
        plan_id=plan_id,
        billing_period=billing_period,
        status=status,
        started_at=started_at,
        ended_at=ended_at,
        trial_ends_at=trial_ends_at,
        stripe_customer_id=stripe_customer_id,
        stripe_subscription_id=stripe_subscription_id,
    )
    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)
    resp = _api_request("patch", f"{_ADMIN}/subscriptions/{subscription_id}", json=body)
    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Updated subscription {subscription_id}[/green]")


@subscriptions_app.command("delete")
def subscriptions_delete(
    subscription_id: str = typer.Argument(..., help="Subscription ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a subscription."""
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete subscription {subscription_id}?", abort=True)
    _api_request("delete", f"{_ADMIN}/subscriptions/{subscription_id}")
    rprint(f"[green]Deleted subscription {subscription_id}[/green]")

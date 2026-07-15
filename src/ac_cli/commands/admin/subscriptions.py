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
    print_detail(
        data,
        [
            ("id", "ID"),
            ("organization_id", "Org"),
            ("plan_id", "Plan"),
            ("billing_period", "Billing"),
            ("billing_mode", "Billing mode"),
            ("status", "Status"),
            ("started_at", "Started"),
            ("ended_at", "Ended"),
            ("trial_ends_at", "Trial Ends"),
            ("stripe_customer_id", "Stripe Customer"),
            ("stripe_subscription_id", "Stripe Sub"),
            ("current_period_end", "Period Ends"),
            ("latest_invoice_url", "Invoice Link"),
            ("last_payment_error", "Payment Error"),
            ("last_payment_decline_code", "Decline Code"),
            # 'do_not_try_again' means the scheduled retry will not execute
            # until the customer supplies a new payment method.
            ("last_payment_advice_code", "Advice Code"),
            ("dunning_attempt_count", "Payment Attempts"),
            ("dunning_next_attempt_at", "Next Retry"),
            ("payment_reminder_count", "Manual Reminders"),
            ("last_payment_reminder_at", "Last Reminder"),
            ("custom_price_cents", "Custom Price (net)"),
            ("unit_amount_cents", "Stripe Amount (net)"),
        ],
    )


@subscriptions_app.command("create")
def subscriptions_create(
    ctx: typer.Context,
    organization_id: str = typer.Option(..., "--org-id", help="Organization ID"),
    plan_id: str = typer.Option(..., "--plan-id", help="Plan ID"),
    billing_period: str = typer.Option(..., "--billing-period", help="monthly | annual"),
    billing_mode: str | None = typer.Option(
        None, "--billing-mode", help="stripe | manual (default stripe)"
    ),
    started_at: str = typer.Option(..., "--started-at", help="ISO start date"),
    status: str | None = typer.Option(None),
    ended_at: str | None = typer.Option(None, "--ended-at"),
    trial_ends_at: str | None = typer.Option(None, "--trial-ends-at"),
    custom_price_cents: int | None = typer.Option(
        None, "--custom-price-cents", help="Per-org net price (cents), off-catalogue"
    ),
    currency: str | None = typer.Option(None, "--currency", help="Price currency"),
    coupon: str | None = typer.Option(None, "--coupon", help="Stripe coupon id"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create a subscription."""
    set_json_mode(json_output)
    # stripe ids are system-managed (activation flow / webhook reconciler) and
    # not client-settable.
    body = _build_body(
        organization_id=organization_id,
        plan_id=plan_id,
        billing_period=billing_period,
        billing_mode=billing_mode,
        started_at=started_at,
        status=status,
        ended_at=ended_at,
        trial_ends_at=trial_ends_at,
        custom_price_cents=custom_price_cents,
        currency=currency,
        coupon=coupon,
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
    billing_mode: str | None = typer.Option(None, "--billing-mode", help="stripe | manual"),
    started_at: str | None = typer.Option(None, "--started-at"),
    ended_at: str | None = typer.Option(None, "--ended-at"),
    trial_ends_at: str | None = typer.Option(None, "--trial-ends-at"),
    custom_price_cents: int | None = typer.Option(
        None, "--custom-price-cents", help="Per-org net price (cents), off-catalogue"
    ),
    currency: str | None = typer.Option(None, "--currency", help="Price currency"),
    coupon: str | None = typer.Option(None, "--coupon", help="Stripe coupon id"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update a subscription."""
    set_json_mode(json_output)
    # status is webhook-authoritative and stripe ids are system-managed; neither
    # is client-settable on update.
    body = _build_body(
        plan_id=plan_id,
        billing_period=billing_period,
        billing_mode=billing_mode,
        started_at=started_at,
        ended_at=ended_at,
        trial_ends_at=trial_ends_at,
        custom_price_cents=custom_price_cents,
        currency=currency,
        coupon=coupon,
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


@subscriptions_app.command("activate-billing")
def subscriptions_activate_billing(
    ctx: typer.Context,
    subscription_id: str = typer.Argument(..., help="Subscription ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Activate a subscription: grant account access AND start billing.

    One action grants the org access and creates the Stripe subscription
    off-session (charging the first period now). If the charge needs
    authentication the subscription stays incomplete and the customer is emailed
    the hosted authorization link.
    """
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(
            f"Activate {subscription_id}? This grants access and charges the card.",
            abort=True,
        )
    resp = _api_request("post", f"{_ADMIN}/subscriptions/{subscription_id}/activate-billing")
    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Activated {subscription_id} (status: {data.get('status')})[/green]")


@subscriptions_app.command("link")
def subscriptions_link(
    ctx: typer.Context,
    subscription_id: str = typer.Argument(..., help="Subscription ID"),
    stripe_subscription_id: str = typer.Option(
        ...,
        "--stripe-subscription-id",
        "--sid",
        help="Existing Stripe subscription ID to link",
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Link a subscription to an existing Stripe subscription.

    Records the association and adopts the live Stripe status; it never creates a
    Stripe subscription and never charges (unlike activate-billing).
    """
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(
            f"Link {subscription_id} to Stripe {stripe_subscription_id}? "
            "(pulls live status; no charge)",
            abort=True,
        )
    resp = _api_request(
        "post",
        f"{_ADMIN}/subscriptions/{subscription_id}/link",
        json={"stripe_subscription_id": stripe_subscription_id},
    )
    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(
            f"[green]Linked {subscription_id} -> {stripe_subscription_id} "
            f"(status: {data.get('status')})[/green]"
        )


@subscriptions_app.command("unlink")
def subscriptions_unlink(
    ctx: typer.Context,
    subscription_id: str = typer.Argument(..., help="Subscription ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Unlink a subscription from its Stripe subscription.

    Clears the local link only; the Stripe subscription is left running.
    """
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Unlink {subscription_id} from its Stripe subscription?", abort=True)
    resp = _api_request("post", f"{_ADMIN}/subscriptions/{subscription_id}/unlink")
    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Unlinked {subscription_id}[/green]")


@subscriptions_app.command("pause")
def subscriptions_pause(
    ctx: typer.Context,
    subscription_id: str = typer.Argument(..., help="Subscription ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Pause billing: Stripe stops collecting until resumed (held invoices void)."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(
            f"Pause billing for {subscription_id}? Stripe stops collecting until resumed.",
            abort=True,
        )
    resp = _api_request("post", f"{_ADMIN}/subscriptions/{subscription_id}/pause")
    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Paused {subscription_id}[/green]")


@subscriptions_app.command("resume")
def subscriptions_resume(
    ctx: typer.Context,
    subscription_id: str = typer.Argument(..., help="Subscription ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Resume billing on the normal cycle after a pause."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Resume billing for {subscription_id}?", abort=True)
    resp = _api_request("post", f"{_ADMIN}/subscriptions/{subscription_id}/resume")
    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Resumed {subscription_id} (status: {data.get('status')})[/green]")


@subscriptions_app.command("switch-comped")
def subscriptions_switch_comped(
    ctx: typer.Context,
    subscription_id: str = typer.Argument(..., help="Subscription ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Cancel Stripe billing and switch the org to free (comped): full access, never billed."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(
            f"Switch {subscription_id} to comped? This cancels the Stripe "
            "subscription immediately and marks the organization comped.",
            abort=True,
        )
    resp = _api_request("post", f"{_ADMIN}/subscriptions/{subscription_id}/switch-comped")
    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Switched {subscription_id} to free (comped)[/green]")


@subscriptions_app.command("send-reminder")
def subscriptions_send_reminder(
    ctx: typer.Context,
    subscription_id: str = typer.Argument(..., help="Subscription ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Email the account owner the hosted invoice link (tracked)."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(
            f"Email the account owner a payment reminder for {subscription_id}?",
            abort=True,
        )
    resp = _api_request("post", f"{_ADMIN}/subscriptions/{subscription_id}/payment-reminder")
    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Reminder sent (total {data.get('payment_reminder_count')})[/green]")


@subscriptions_app.command("worklists")
def subscriptions_worklists(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """Show the awaiting-activation queue and the stuck / needs-attention bucket."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_ADMIN}/subscriptions/worklists")
    data = resp.json()
    if json_output:
        print_json(data)
        return
    columns = [
        ("organization_name", "Org"),
        ("onboarding_status", "Onboarding"),
        ("subscription_status", "Sub Status"),
        ("card_last4", "Card"),
        ("reason", "Reason"),
    ]
    awaiting = data.get("awaiting_activation", [])
    stuck = data.get("stuck", [])
    overdue = data.get("overdue", [])
    print_table(overdue, columns, title=f"Payment overdue ({len(overdue)})")
    print_table(
        awaiting,
        columns,
        title=f"Awaiting activation ({len(awaiting)})",
    )
    print_table(stuck, columns, title=f"Stuck / needs attention ({len(stuck)})")

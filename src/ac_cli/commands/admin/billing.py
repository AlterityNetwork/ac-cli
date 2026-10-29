"""Admin billing commands."""

from __future__ import annotations

import uuid

import typer

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    _build_body,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.commands.admin import _ADMIN
from ac_cli.formatting import print_detail, print_json, print_table

billing_app = typer.Typer(help="Admin billing views (super admin)")


@billing_app.command("stripe-subscriptions")
def stripe_subscriptions(
    ctx: typer.Context,
    limit: int = typer.Option(50, help="Max results"),
    offset: int = typer.Option(0, help="Pagination offset"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List live Stripe subscriptions with their local link status.

    Each Stripe subscription shows the linked local subscription id (or that it
    is an orphan). ``broken_links`` flags local rows whose Stripe subscription no
    longer exists. The Stripe list is paginated (``--limit`` / ``--offset``); the
    broken-links set is always complete.
    """
    set_json_mode(json_output)
    resp = _api_request(
        "get",
        f"{_ADMIN}/billing/stripe-subscriptions",
        params={"limit": limit, "offset": offset},
    )
    data = resp.json()
    if json_output:
        print_json(data)
        return
    items = data.get("data", [])
    print_table(
        items,
        [
            ("id", "Stripe Sub"),
            ("customer_id", "Customer"),
            ("status", "Status"),
            ("amount", "Amount"),
            ("currency", "Currency"),
            ("linked_local_subscription_id", "Linked Local"),
            ("is_orphan", "Orphan"),
        ],
        title=f"Stripe subscriptions ({data.get('total', len(items))})",
    )
    broken = data.get("broken_links", [])
    if broken:
        print_table(
            broken,
            [
                ("local_subscription_id", "Local Sub"),
                ("organization_id", "Org"),
                ("stripe_subscription_id", "Missing Stripe Sub"),
            ],
            title=f"Broken links ({len(broken)})",
        )


@billing_app.command("import-stripe-products")
def import_stripe_products(
    ctx: typer.Context,
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Import active Stripe products and recurring prices into the plan catalogue.

    Idempotent: each active Stripe product with a recurring price is matched to a
    subscription plan by ``stripe_product_id`` (prices / name updated) or created
    as a new plan. Products with no recurring price are skipped. Reports per-run
    counts plus any notes (e.g. a product missing a monthly or annual price).
    """
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm("Import active Stripe products into the plan catalogue?", abort=True)
    resp = _api_request("post", f"{_ADMIN}/billing/import-stripe-products")
    data = resp.json()
    if json_output:
        print_json(data)
        return
    print_detail(
        data,
        [
            ("imported", "Imported"),
            ("updated", "Updated"),
            ("skipped", "Skipped"),
        ],
    )
    for message in data.get("messages") or []:
        typer.echo(f"  - {message}")


@billing_app.command("refund")
def billing_refund(
    ctx: typer.Context,
    charge_id: str = typer.Argument(..., help="Stripe charge ID (ch_...)"),
    amount_cents: int | None = typer.Option(
        None, "--amount-cents", help="Partial refund in minor units; omit for full"
    ),
    reason: str | None = typer.Option(
        None,
        "--reason",
        help="duplicate | fraudulent | requested_by_customer",
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Refund a charge on-app (audited), full or partial."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        label = f"{amount_cents} minor units" if amount_cents else "the full amount"
        typer.confirm(f"Refund {label} of charge {charge_id}?", abort=True)
    body = _build_body(charge_id=charge_id, amount_cents=amount_cents, reason=reason)
    resp = _api_request("post", f"{_ADMIN}/billing/refunds", json=body)
    data = resp.json()
    if json_output:
        print_json(data)
        return
    print_detail(
        data,
        [
            ("id", "Refund"),
            ("status", "Status"),
            ("amount", "Amount (minor units)"),
            ("currency", "Currency"),
            ("charge", "Charge"),
        ],
    )


@billing_app.command("top-up")
def billing_top_up(
    ctx: typer.Context,
    organization_id: str = typer.Option(..., "--org-id", help="Organization ID"),
    credits: int = typer.Option(..., "--credits", help="Credits to add, 100 to 1,000,000"),
    request_id: str | None = typer.Option(
        None,
        "--request-id",
        help="UUID that keys the Stripe calls; repeat it to retry without a second charge",
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Charge a credit top-up to the organization's saved payment method.

    The invoice is the credits at GBP 0.01 each, with tax on top. The credits
    are added when Stripe reports the invoice paid, and they count in the
    current credit period only.
    """
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(
            f"Charge £{credits / 100:,.2f} plus tax for {credits:,} credits to "
            f"organization {organization_id}?",
            abort=True,
        )
    body = {
        "organization_id": organization_id,
        "credits": credits,
        "request_id": request_id or str(uuid.uuid4()),
    }
    resp = _api_request("post", f"{_ADMIN}/billing/top-ups", json=body)
    data = resp.json()
    if json_output:
        print_json(data)
        return
    print_detail(
        data,
        [
            ("invoice_id", "Invoice"),
            ("status", "Status"),
            ("credits", "Credits"),
            ("amount_pence", "Net (pence)"),
            ("total_pence", "Total with tax (pence)"),
            ("currency", "Currency"),
        ],
    )


@billing_app.command("credit-usage")
def billing_credit_usage(
    ctx: typer.Context,
    attention: bool = typer.Option(
        False, "--attention", help="Only organizations at 80 percent of their credits or more"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """List the credit balance of every organization in its current period."""
    set_json_mode(json_output)
    resp = _api_request(
        "get",
        f"{_ADMIN}/billing/credit-usage",
        params={"attention": str(attention).lower()},
    )
    data = resp.json()
    if json_output:
        print_json(data)
        return
    items = [
        {
            **row,
            "used": f"{row['used_percent']}%" if row.get("used_percent") is not None else "-",
        }
        for row in data.get("organizations") or []
    ]
    print_table(
        items,
        [
            ("organization_name", "Organization"),
            ("allowance", "Allowance"),
            ("top_ups", "Top-ups"),
            ("spent", "Spent"),
            ("balance", "Balance"),
            ("used", "Used"),
            ("state", "State"),
            ("card_last4", "Card"),
            ("organization_id", "ID"),
        ],
        title=f"Credit usage ({len(items)})",
    )

"""Admin billing commands."""

from __future__ import annotations

import typer

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
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
    for message in data.get("messages", []):
        typer.echo(f"  - {message}")

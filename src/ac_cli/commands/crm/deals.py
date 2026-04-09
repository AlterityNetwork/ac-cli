"""CRM deals commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _resolve_company_id,
    _resolve_contact_id,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.commands.crm import _CRM, _api_request, _build_body
from ac_cli.formatting import print_detail, print_json, print_table

deals_app = typer.Typer(help="Deal operations")


@deals_app.command("list")
def deals_list(
    ctx: typer.Context,
    stage: str | None = typer.Option(None, help="Filter by stage"),
    company_id: str | None = typer.Option(None, "--company-id", help="Filter by company"),
    owner_id: str | None = typer.Option(None, "--owner-id", help="Filter by owner"),
    limit: int = typer.Option(100, help="Max results"),
    offset: int = typer.Option(0, help="Offset"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List deals."""
    set_json_mode(json_output)
    params: dict = {"limit": limit, "offset": offset}
    if stage:
        params["stage"] = stage
    if company_id:
        params["company_id"] = company_id
    if owner_id:
        params["owner_user_id"] = owner_id

    resp = _api_request("get", f"{_CRM}/deals", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    # API returns a flat list
    items = data if isinstance(data, list) else data.get("data", [])
    print_table(
        items,
        [
            ("name", "Name"),
            ("stage", "Stage"),
            ("amount", "Amount"),
            ("expected_close_date", "Close Date"),
            ("id", "ID"),
        ],
        title=f"Deals ({len(items)})",
    )


@deals_app.command("get")
def deals_get(
    ctx: typer.Context,
    deal_id: str = typer.Argument(..., help="Deal ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get a deal by ID."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_CRM}/deals/{deal_id}")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(data, [
        ("id", "ID"),
        ("name", "Name"),
        ("stage", "Stage"),
        ("amount", "Amount"),
        ("currency", "Currency"),
        ("probability", "Probability"),
        ("expected_close_date", "Expected Close"),
        ("actual_close_date", "Actual Close"),
        ("company_id", "Company ID"),
        ("primary_contact_id", "Contact ID"),
        ("owner_user_id", "Owner ID"),
        ("tags", "Tags"),
        ("next_steps", "Next Steps"),
        ("lost_reason", "Lost Reason"),
        ("created_at", "Created"),
        ("updated_at", "Updated"),
    ])


@deals_app.command("create")
def deals_create(
    ctx: typer.Context,
    name: str = typer.Option(..., help="Deal name"),
    stage: str | None = typer.Option(None, help="Deal stage"),
    amount: float | None = typer.Option(None, help="Deal amount"),
    currency: str | None = typer.Option(None, help="Currency code"),
    company_id: str | None = typer.Option(None, "--company-id", help="Company ID"),
    company_name: str | None = typer.Option(None, "--company-name", help="Company name (auto-resolves to ID)"),
    contact_id: str | None = typer.Option(None, "--contact-id", help="Primary contact ID"),
    contact_name: str | None = typer.Option(None, "--contact-name", help="Contact name (auto-resolves to ID)"),
    expected_close_date: str | None = typer.Option(None, "--expected-close-date", help="ISO date"),
    tags: str | None = typer.Option(None, help="Comma-separated tags"),
    next_steps: str | None = typer.Option(None, "--next-steps", help="Next steps"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create a new deal."""
    set_json_mode(json_output)
    resolved_company = _resolve_company_id(company_id, company_name, _CRM)
    resolved_contact = _resolve_contact_id(contact_id, contact_name, _CRM)
    body = _build_body(
        name=name, stage=stage, amount=amount, currency=currency,
        company_id=resolved_company, expected_close_date=expected_close_date,
        tags=tags, next_steps=next_steps,
    )
    if resolved_contact is not None:
        body["primary_contact_id"] = resolved_contact

    me = _api_request("get", "/whoami")
    body["organization_id"] = me.json()["organization_id"]

    resp = _api_request("post", f"{_CRM}/deals", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Created deal:[/green] {data['name']} ({data['id']})")


@deals_app.command("update")
def deals_update(
    ctx: typer.Context,
    deal_id: str = typer.Argument(..., help="Deal ID"),
    name: str | None = typer.Option(None, help="Deal name"),
    stage: str | None = typer.Option(None, help="Deal stage"),
    amount: float | None = typer.Option(None, help="Deal amount"),
    currency: str | None = typer.Option(None, help="Currency code"),
    company_id: str | None = typer.Option(None, "--company-id", help="Company ID"),
    company_name: str | None = typer.Option(None, "--company-name", help="Company name (auto-resolves to ID)"),
    contact_id: str | None = typer.Option(None, "--contact-id", help="Primary contact ID"),
    contact_name: str | None = typer.Option(None, "--contact-name", help="Contact name (auto-resolves to ID)"),
    expected_close_date: str | None = typer.Option(None, "--expected-close-date", help="ISO date"),
    tags: str | None = typer.Option(None, help="Comma-separated tags"),
    next_steps: str | None = typer.Option(None, "--next-steps", help="Next steps"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update an existing deal."""
    set_json_mode(json_output)
    resolved_company = _resolve_company_id(company_id, company_name, _CRM)
    resolved_contact = _resolve_contact_id(contact_id, contact_name, _CRM)
    body = _build_body(
        name=name, stage=stage, amount=amount, currency=currency,
        company_id=resolved_company, expected_close_date=expected_close_date,
        tags=tags, next_steps=next_steps,
    )
    if resolved_contact is not None:
        body["primary_contact_id"] = resolved_contact

    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    resp = _api_request("patch", f"{_CRM}/deals/{deal_id}", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Updated deal:[/green] {data['name']} ({data['id']})")


@deals_app.command("move")
def deals_move(
    ctx: typer.Context,
    deal_id: str = typer.Argument(..., help="Deal ID"),
    stage: str = typer.Option(..., help="New stage"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Move a deal to a new stage."""
    set_json_mode(json_output)
    resp = _api_request("patch", f"{_CRM}/deals/{deal_id}/stage", json={"stage": stage})

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Moved deal to {data['stage']}:[/green] {data['name']} ({data['id']})")


@deals_app.command("order")
def deals_order(
    ctx: typer.Context,
    stage: str = typer.Option(..., help="Stage to reorder deals in"),
    deal_ids: str = typer.Option(..., "--deal-ids", help="Comma-separated ordered deal IDs"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Set the display order of deals within a stage."""
    set_json_mode(json_output)
    ids_list = [d.strip() for d in deal_ids.split(",")]
    resp = _api_request("post", f"{_CRM}/deals/order", json={"stage": stage, "deal_ids": ids_list})

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Reordered {len(ids_list)} deals in stage '{stage}'[/green]")


@deals_app.command("delete")
def deals_delete(
    deal_id: str = typer.Argument(..., help="Deal ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a deal."""
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete deal {deal_id}?", abort=True)

    _api_request("delete", f"{_CRM}/deals/{deal_id}")

    rprint(f"[green]Deleted deal {deal_id}[/green]")

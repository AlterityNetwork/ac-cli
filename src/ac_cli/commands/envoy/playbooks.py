"""Envoy playbooks commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,
    _build_body,
    refuse_local,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.formatting import print_detail, print_json, print_table, styled

# Playbooks moved out of /envoy to top-level /api/v1/playbooks (ENG-592).
_PLAYBOOKS = "/api/v1/playbooks"

playbooks_app = typer.Typer(help="Playbook operations")

_DOCUMENT_HELP = "Vault document id the offer attaches. Repeat for several."
_ICP_IDS_HELP = "Ideal customer profile id. Repeat for several."


def _with_document_count(row: dict) -> dict:
    """Returns the row with a `documents` count of its document ids."""
    return {**row, "documents": len(row.get("document_ids") or [])}


@playbooks_app.command("list")
def playbooks_list(
    ctx: typer.Context,
    query: str | None = typer.Option(None, "--query", "-q", help="Search query"),
    limit: int | None = typer.Option(None, help="Max results to return"),
    offset: int | None = typer.Option(None, help="Row offset"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List playbooks."""
    set_json_mode(json_output)
    params: dict = {}
    if query:
        params["q"] = query
    if limit is not None:
        params["limit"] = limit
    if offset is not None:
        params["offset"] = offset

    resp = _api_request("get", f"{_PLAYBOOKS}", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("data", [])
    print_table(
        [_with_document_count(item) for item in items],
        [
            ("name", "Name"),
            ("offer", "Offer"),
            ("cta", "CTA"),
            ("documents", "Documents"),
            ("id", "ID"),
        ],
        title=f"Playbooks ({len(items)})",
    )


@playbooks_app.command("get")
def playbooks_get(
    ctx: typer.Context,
    playbook_id: str = typer.Argument(..., help="Playbook ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get a playbook by ID."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_PLAYBOOKS}/{playbook_id}")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(
        {**data, "document_ids": ", ".join(data.get("document_ids") or [])},
        [
            ("id", "ID"),
            ("name", "Name"),
            ("icp", "ICP"),
            ("offer", "Offer"),
            ("cta", "CTA"),
            ("cta_link", "CTA Link"),
            ("document_ids", "Documents"),
            ("created_at", "Created"),
        ],
    )


@playbooks_app.command("create")
def playbooks_create(
    ctx: typer.Context,
    name: str = typer.Option(..., help="Playbook name"),
    icp: str | None = typer.Option(None, "--icp", help="Ideal customer profile, as text"),
    offer: str | None = typer.Option(None, "--offer", help="Offer or value proposition"),
    cta: str | None = typer.Option(None, "--cta", help="Call-to-action text"),
    cta_link: str | None = typer.Option(None, "--cta-link", help="Call-to-action URL"),
    icp_ids: list[str] | None = typer.Option(None, "--icp-id", help=_ICP_IDS_HELP),
    documents: list[str] | None = typer.Option(None, "--document", help=_DOCUMENT_HELP),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create a new playbook."""
    set_json_mode(json_output)
    body = _build_body(
        name=name,
        icp=icp,
        offer=offer,
        cta=cta,
        cta_link=cta_link,
        icp_ids=icp_ids,
        document_ids=documents or None,
    )

    resp = _api_request("post", f"{_PLAYBOOKS}", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(styled("[green]Created playbook:[/green] {} ({})", data["name"], data["id"]))


@playbooks_app.command("update")
def playbooks_update(
    ctx: typer.Context,
    playbook_id: str = typer.Argument(..., help="Playbook ID"),
    name: str | None = typer.Option(None, help="Playbook name"),
    icp: str | None = typer.Option(None, "--icp", help="Ideal customer profile, as text"),
    offer: str | None = typer.Option(None, "--offer", help="Offer or value proposition"),
    cta: str | None = typer.Option(None, "--cta", help="Call-to-action text"),
    cta_link: str | None = typer.Option(None, "--cta-link", help="Call-to-action URL"),
    icp_ids: list[str] | None = typer.Option(None, "--icp-id", help=_ICP_IDS_HELP),
    documents: list[str] | None = typer.Option(
        None, "--document", help=f"{_DOCUMENT_HELP} Replaces the current documents."
    ),
    clear_documents: bool = typer.Option(
        False, "--clear-documents", help="Remove every attached document"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update a playbook."""
    set_json_mode(json_output)
    if documents and clear_documents:
        refuse_local("Use --document or --clear-documents, not both")
    body = _build_body(
        name=name,
        icp=icp,
        offer=offer,
        cta=cta,
        cta_link=cta_link,
        icp_ids=icp_ids,
        document_ids=documents or ([] if clear_documents else None),
    )

    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    resp = _api_request("patch", f"{_PLAYBOOKS}/{playbook_id}", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(styled("[green]Updated playbook:[/green] {} ({})", data["name"], data["id"]))


@playbooks_app.command("delete")
def playbooks_delete(
    playbook_id: str = typer.Argument(..., help="Playbook ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a playbook."""
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete playbook {playbook_id}?", abort=True)

    _api_request("delete", f"{_PLAYBOOKS}/{playbook_id}")

    rprint(styled("[green]Deleted playbook {}[/green]", playbook_id))


@playbooks_app.command("duplicate")
def playbooks_duplicate(
    ctx: typer.Context,
    playbook_id: str = typer.Argument(..., help="Playbook ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Duplicate a playbook."""
    set_json_mode(json_output)
    resp = _api_request("post", f"{_PLAYBOOKS}/{playbook_id}/duplicate")

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(styled("[green]Duplicated playbook:[/green] {} ({})", data["name"], data["id"]))

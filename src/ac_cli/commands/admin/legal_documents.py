"""Admin legal document management commands."""

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
from ac_cli.formatting import print_detail, print_json, print_table, styled

legal_docs_app = typer.Typer(help="Legal document management")


@legal_docs_app.command("list")
def legal_docs_list(
    ctx: typer.Context,
    document_type: str | None = typer.Option(
        None, "--document-type", help="Filter by document type"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """List legal documents."""
    set_json_mode(json_output)
    params: dict = {}
    if document_type:
        params["document_type"] = document_type

    resp = _api_request("get", f"{_ADMIN}/legal-documents", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("items", [])
    print_table(
        items,
        [
            ("id", "ID"),
            ("document_type", "Type"),
            ("version", "Version"),
            ("title", "Title"),
            ("is_current", "Current"),
            ("published_at", "Published"),
        ],
        title="Legal Documents",
    )


@legal_docs_app.command("get")
def legal_docs_get(
    ctx: typer.Context,
    document_id: str = typer.Argument(..., help="Document ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get a legal document by ID."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_ADMIN}/legal-documents/{document_id}")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(
        data,
        [
            ("id", "ID"),
            ("document_type", "Type"),
            ("version", "Version"),
            ("title", "Title"),
            ("content_html", "Content HTML"),
            ("is_current", "Current"),
            ("published_at", "Published"),
            ("created_at", "Created"),
            ("updated_at", "Updated"),
        ],
    )


@legal_docs_app.command("create")
def legal_docs_create(
    ctx: typer.Context,
    document_type: str = typer.Option(..., "--document-type", help="Document type"),
    version: str = typer.Option(..., help="Document version"),
    title: str = typer.Option(..., help="Document title"),
    content_html: str | None = typer.Option(None, "--content-html", help="HTML content"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Create a new legal document."""
    set_json_mode(json_output)
    body = _build_body(
        document_type=document_type,
        version=version,
        title=title,
        content_html=content_html,
    )

    resp = _api_request("post", f"{_ADMIN}/legal-documents", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(styled("[green]Created legal document:[/green] {} ({})", data["title"], data["id"]))


@legal_docs_app.command("update")
def legal_docs_update(
    ctx: typer.Context,
    document_id: str = typer.Argument(..., help="Document ID"),
    title: str | None = typer.Option(None, help="Document title"),
    content_html: str | None = typer.Option(None, "--content-html", help="HTML content"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update an existing legal document."""
    set_json_mode(json_output)
    body = _build_body(
        title=title,
        content_html=content_html,
    )

    if not body:
        rprint("[yellow]No fields to update.[/yellow]")
        raise typer.Exit(code=1)

    resp = _api_request("patch", f"{_ADMIN}/legal-documents/{document_id}", json=body)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(styled("[green]Updated legal document:[/green] {} ({})", data["title"], data["id"]))


@legal_docs_app.command("delete")
def legal_docs_delete(
    ctx: typer.Context,
    document_id: str = typer.Argument(..., help="Document ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Delete a legal document."""
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete legal document {document_id}?", abort=True)

    _api_request("delete", f"{_ADMIN}/legal-documents/{document_id}")

    rprint(styled("[green]Deleted legal document {}[/green]", document_id))


@legal_docs_app.command("set-current")
def legal_docs_set_current(
    ctx: typer.Context,
    document_id: str = typer.Argument(..., help="Document ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Set a legal document as the current version."""
    set_json_mode(json_output)
    resp = _api_request("post", f"{_ADMIN}/legal-documents/{document_id}/set-current")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(
        data,
        [
            ("id", "ID"),
            ("document_type", "Type"),
            ("version", "Version"),
            ("title", "Title"),
            ("is_current", "Current"),
            ("published_at", "Published"),
        ],
    )

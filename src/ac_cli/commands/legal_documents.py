"""Legal documents commands (user-facing)."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import JSON_OPTION, _api_request, set_json_mode
from ac_cli.formatting import as_text, print_detail, print_json, styled

app = typer.Typer(help="Legal documents")

_LEGAL = "/api/v1/legal-documents"


@app.callback()
def legal_callback(ctx: typer.Context) -> None:
    ctx.ensure_object(dict)


@app.command("current")
def get_current(
    ctx: typer.Context,
    document_type: str = typer.Argument(
        ..., help="Document type (e.g. terms-of-service, privacy-policy)"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get the current version of a legal document."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_LEGAL}/current/{document_type}")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(
        data,
        [
            ("id", "ID"),
            ("type", "Type"),
            ("version", "Version"),
            ("effective_date", "Effective Date"),
            ("url", "URL"),
        ],
    )


@app.command("status")
def get_status(
    ctx: typer.Context,
    document_type: str = typer.Argument(..., help="Document type"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Check acceptance status for a legal document."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_LEGAL}/status/{document_type}")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    accepted = data.get("accepted", False)
    status = "[green]Accepted[/green]" if accepted else "[yellow]Not accepted[/yellow]"
    rprint("Status:", status)
    if data.get("accepted_version"):
        rprint(as_text(f"  Version: {data['accepted_version']}"))
    if data.get("accepted_at"):
        rprint(as_text(f"  Accepted at: {data['accepted_at']}"))


@app.command("accept")
def accept(
    ctx: typer.Context,
    document_type: str = typer.Argument(..., help="Document type"),
    version: str = typer.Option(..., "--version", "-v", help="Document version to accept"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Accept a legal document."""
    set_json_mode(json_output)
    resp = _api_request(
        "post", f"{_LEGAL}/accept", json={"document_type": document_type, "version": version}
    )

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(styled("[green]Accepted {} version {}[/green]", document_type, version))

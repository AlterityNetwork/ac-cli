"""Knowledge base resource commands."""

from __future__ import annotations

import mimetypes
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import typer
from rich import print as rprint

from ac_cli.client import get_api_client
from ac_cli.commands._helpers import (
    _EXIT_CODES,
    JSON_OPTION,
    _api_request,
    _handle_connection_error,
    _handle_error,
    _json_output,
    refuse_local,
    set_json_mode,
    should_skip_confirm,
)
from ac_cli.formatting import as_text, print_detail, print_json, print_table, styled

app = typer.Typer(help="Knowledge base resources")

_RESOURCES = "/api/v1/resources"

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}
MAX_SIZE_BYTES = 10_485_760  # 10 MB


@app.callback()
def resources_callback(ctx: typer.Context) -> None:
    ctx.ensure_object(dict)


@app.command("list")
def resources_list(
    ctx: typer.Context,
    limit: int = typer.Option(50, help="Max items to return"),
    offset: int = typer.Option(0, help="Offset for pagination"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List the documents of your organisation.

    The list holds every document of the organisation, not only the ones you
    uploaded.
    """
    set_json_mode(json_output)
    params: dict = {"limit": limit, "offset": offset}
    resp = _api_request("get", _RESOURCES, params=params)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data.get("data", [])
    if not items:
        rprint("[dim]No resources found.[/dim]")
        return

    print_table(
        items,
        [
            ("id", "ID"),
            ("source_name", "Source Name"),
            ("status", "Status"),
            ("created_at", "Created"),
        ],
        title=f"Resources ({data.get('total', '?')} total)",
    )


@app.command("upload")
def resources_upload(
    ctx: typer.Context,
    file_path: Path = typer.Argument(..., help="Path to the resource file"),
    name: str = typer.Option(..., "--name", help="Source name for the resource"),
    description: str | None = typer.Option(None, "--description", help="Resource description"),
    tags: str | None = typer.Option(None, "--tags", help="Comma-separated tags"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Upload a knowledge base resource file."""
    set_json_mode(json_output)
    if not file_path.exists():
        rprint(styled("[red]Error:[/red] File not found: {}", file_path))
        raise typer.Exit(code=1)

    suffix = file_path.suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        rprint(styled("[red]Error:[/red] Unsupported file type: {}", suffix))
        raise typer.Exit(code=1)

    size = file_path.stat().st_size
    if size > MAX_SIZE_BYTES:
        rprint(styled("[red]Error:[/red] File too large ({} bytes, max {})", size, MAX_SIZE_BYTES))
        raise typer.Exit(code=1)

    content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"

    form_data: dict = {"source_name": name}
    if description is not None:
        form_data["description"] = description
    if tags is not None:
        form_data["tags"] = tags

    with open(file_path, "rb") as f:
        resp = _api_request(
            "post",
            f"{_RESOURCES}/upload",
            files={"file": (file_path.name, f, content_type)},
            data=form_data,
        )

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(
            styled(
                "[green]Uploaded resource:[/green] {} ({})",
                data.get("source_name", name),
                data.get("id", ""),
            )
        )


def _in_use_context(exc: httpx.HTTPStatusError) -> dict | None:
    """Returns the context of a `resource_in_use` refusal, or None."""
    if exc.response.status_code != 409:
        return None
    try:
        body = exc.response.json()
    except ValueError:
        return None
    context = body.get("context") if isinstance(body, dict) else None
    if not isinstance(context, dict):
        return None
    if "resource_in_use" not in (body.get("code"), context.get("code")):
        return None
    return context


def _print_in_use(resource_id: str, context: dict) -> None:
    """Prints the offers and sequence steps that attach one document."""
    rprint(styled("[red]Error 409:[/red] Document {} is in use.", resource_id))
    for offer in context.get("offers") or []:
        rprint(as_text(f"  Offer: {offer.get('name') or offer.get('id')}"))
    for step in context.get("steps") or []:
        sequence = step.get("sequence_name") or step.get("sequence_id")
        name = step.get("step_name") or step.get("id")
        rprint(as_text(f"  Sequence step: {sequence} / {name}"))
    rprint("Run the command again with --force to remove it from each and delete it.")


@app.command("delete")
def resources_delete(
    ctx: typer.Context,
    resource_id: str = typer.Argument(..., help="Resource ID"),
    force: bool = typer.Option(
        False,
        "--force",
        help="Remove the document from every offer and sequence step that attaches it",
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Delete a knowledge base resource.

    The API refuses a document that an offer or a sequence step attaches. The
    refusal names each offer and step. Use --force to delete it anyway.
    """
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Delete resource {resource_id}?", abort=True)

    params = {"force": "true"} if force else None
    with get_api_client() as client:
        try:
            client.delete(f"{_RESOURCES}/{resource_id}", params=params).raise_for_status()
        except httpx.HTTPStatusError as exc:
            context = _in_use_context(exc)
            if context is None or _json_output.get():
                _handle_error(exc)
            _print_in_use(resource_id, context)
            raise typer.Exit(code=_EXIT_CODES[409]) from None
        except httpx.HTTPError as exc:
            _handle_connection_error(exc)

    if json_output:
        print_json({"deleted": True, "id": resource_id})
    else:
        rprint(styled("[green]Deleted resource {}[/green]", resource_id))


@app.command("status")
def resources_status(
    ctx: typer.Context,
    resource_id: str = typer.Argument(..., help="Resource ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get processing status for a knowledge base resource."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_RESOURCES}/{resource_id}/status")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(
        data,
        [
            ("id", "ID"),
            ("status", "Status"),
            ("chunk_count", "Chunk Count"),
            ("error_message", "Error"),
            ("source_description", "Description"),
            ("image_url", "Thumbnail"),
        ],
    )


share_app = typer.Typer(help="Share links of a document: a hosted preview page that counts opens")
app.add_typer(share_app, name="share")

_EXPIRES_IN_DAYS_HELP = "Expire the link this many days from now (the UI presets are 7, 30, 90)"


def _expires_at(days: int) -> str:
    """Returns the ISO time `days` days from now, in UTC.

    Args:
        days: The number of days. It must be 1 or more.

    Raises:
        typer.Exit: The number is less than 1.
    """
    if days < 1:
        refuse_local("--expires-in-days must be 1 or more", days)
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _print_link(label: str, link: dict) -> None:
    """Prints the URL of a share link on its own line, then its state."""
    rprint(styled("[green]{}:[/green]", label))
    rprint(as_text(link.get("url") or ""))
    rprint(as_text(f"  ID: {link.get('id')}"))
    rprint(as_text(f"  Status: {link.get('status')}"))
    rprint(as_text(f"  Expires: {link.get('expires_at') or 'never'}"))


@share_app.command("create")
def share_create(
    ctx: typer.Context,
    resource_id: str = typer.Argument(..., help="Resource ID"),
    expires_in_days: int | None = typer.Option(
        None, "--expires-in-days", help=_EXPIRES_IN_DAYS_HELP
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Get or create the public share link of a document.

    A document has one public link. When the link exists and is not revoked,
    the API returns it unchanged and ignores --expires-in-days. Use
    `ac resources share update` to change its expiry.
    """
    set_json_mode(json_output)
    expires_at = None if expires_in_days is None else _expires_at(expires_in_days)
    resp = _api_request(
        "post",
        f"{_RESOURCES}/{resource_id}/share-links",
        json={"expires_at": expires_at},
    )

    data = resp.json()
    if json_output:
        print_json(data)
        return

    _print_link("Share link", data)
    if data.get("status") != "active":
        rprint(
            as_text(
                "  The link is not active. Run `ac resources share update` to set a new expiry."
            )
        )


@share_app.command("list")
def share_list(
    ctx: typer.Context,
    resource_id: str = typer.Argument(..., help="Resource ID"),
    limit: int = typer.Option(50, help="Max items to return"),
    offset: int = typer.Option(0, help="Offset for pagination"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List every share link of a document, public and recipient, newest first."""
    set_json_mode(json_output)
    resp = _api_request(
        "get",
        f"{_RESOURCES}/{resource_id}/share-links",
        params={"limit": limit, "offset": offset},
    )

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data.get("data", [])
    if not items:
        rprint("[dim]No share links found.[/dim]")
        return

    print_table(
        items,
        [
            ("id", "ID"),
            ("kind", "Kind"),
            ("status", "Status"),
            ("open_count", "Opens"),
            ("last_opened_at", "Last Opened"),
            ("crm_person_name", "Person"),
            ("url", "URL"),
        ],
        title=f"Share links ({data.get('total', '?')} total)",
    )


@share_app.command("update")
def share_update(
    ctx: typer.Context,
    link_id: str = typer.Argument(..., help="Share link ID"),
    expires_in_days: int | None = typer.Option(
        None, "--expires-in-days", help=_EXPIRES_IN_DAYS_HELP
    ),
    no_expiry: bool = typer.Option(False, "--no-expiry", help="Remove the expiry of the link"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Set or remove the expiry of a share link.

    Give --expires-in-days or --no-expiry, and not both. The API refuses a
    revoked link with 404.
    """
    set_json_mode(json_output)
    if (expires_in_days is None) == (not no_expiry):
        refuse_local("Give --expires-in-days or --no-expiry, and not both")
    expires_at = None if no_expiry else _expires_at(expires_in_days)
    resp = _api_request(
        "patch",
        f"{_RESOURCES}/share-links/{link_id}",
        json={"expires_at": expires_at},
    )

    data = resp.json()
    if json_output:
        print_json(data)
        return
    _print_link("Updated share link", data)


@share_app.command("revoke")
def share_revoke(
    ctx: typer.Context,
    link_id: str = typer.Argument(..., help="Share link ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Revoke a share link.

    The link stops working for every person who has it. Revoking a public link
    also revokes the recipient links that the sent emails hold.
    """
    set_json_mode(json_output)
    if not should_skip_confirm(yes):
        typer.confirm(f"Revoke share link {link_id}? Nobody can open it after this.", abort=True)

    resp = _api_request("post", f"{_RESOURCES}/share-links/{link_id}/revoke")

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(styled("[green]Revoked share link {}[/green]", link_id))


@share_app.command("opens")
def share_opens(
    ctx: typer.Context,
    link_id: str = typer.Argument(..., help="Share link ID"),
    limit: int = typer.Option(50, help="Max items to return"),
    offset: int = typer.Option(0, help="Offset for pagination"),
    json_output: bool = JSON_OPTION,
) -> None:
    """List the opens of a share link, newest first.

    A view is an open of the hosted page. A download is a download of the file.
    """
    set_json_mode(json_output)
    resp = _api_request(
        "get",
        f"{_RESOURCES}/share-links/{link_id}/opens",
        params={"limit": limit, "offset": offset},
    )

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data.get("data", [])
    if not items:
        rprint("[dim]No opens found.[/dim]")
        return

    print_table(
        items,
        [
            ("opened_at", "Opened"),
            ("kind", "Kind"),
            ("user_agent", "User Agent"),
        ],
        title=f"Opens ({data.get('total', '?')} total)",
    )

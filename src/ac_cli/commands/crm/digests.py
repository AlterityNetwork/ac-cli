"""CRM digest commands.

Mirrors ``/api/v1/crm/digests/*`` on ac-python-api: preview the
caller's nightly digest, or trigger an on-demand test send.
"""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import JSON_OPTION, set_json_mode
from ac_cli.commands.crm import _CRM, _api_request
from ac_cli.formatting import print_json

digests_app = typer.Typer(help="CRM nightly digest operations")


@digests_app.command("preview")
def digest_preview(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """Preview today's per-owner digest without dispatching it."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_CRM}/digests/preview")
    data = resp.json()
    if json_output:
        print_json(data)
        return

    payload = data.get("payload") or {}
    digest_date = payload.get("digest_date", "?")
    rprint(f"\n[bold]CRM digest preview[/bold] — {digest_date}\n")
    rprint(payload.get("markdown") or "[dim](empty digest)[/dim]")


@digests_app.command("test-send")
def digest_test_send(
    ctx: typer.Context,
    to: str = typer.Option(
        None,
        "--to",
        help=(
            "Redirect the email to this address (superadmin-only). Skips the "
            "in-app notification dispatch so the digest does not land in "
            "another user's bell."
        ),
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Dispatch a digest to your inbox now (and email if you've opted in)."""
    set_json_mode(json_output)
    body = {"recipient_email": to} if to else None
    resp = _api_request("post", f"{_CRM}/digests/test-send", json=body)
    data = resp.json()
    if json_output:
        print_json(data)
        return

    if data.get("is_empty"):
        rprint("[dim]No signals to digest right now — nothing dispatched.[/dim]")
        return

    notif_id = data.get("notification_id")
    if notif_id:
        rprint(f"[green]✓[/green] In-app notification sent (id={notif_id}).")
    elif to:
        rprint("[dim]In-app dispatch skipped (email override mode).[/dim]")
    else:
        rprint("[yellow]⚠[/yellow] In-app notification deduped or muted.")
    if data.get("email_sent"):
        target = data.get("recipient_email") or to or "your inbox"
        rprint(f"[green]✓[/green] Email dispatched to {target}.")
    else:
        rprint("[dim]Email not sent (opt-in via /settings/notifications to enable).[/dim]")

"""Nylas email integration commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import JSON_OPTION, _api_request, _build_body, set_json_mode, should_skip_confirm
from ac_cli.formatting import print_detail, print_json, print_table

app = typer.Typer(help="Nylas email integration")

_NYLAS = "/api/v1/nylas"


@app.callback()
def nylas_callback(ctx: typer.Context) -> None:
    ctx.ensure_object(dict)


@app.command("oauth-start")
def oauth_start(
    ctx: typer.Context,
    provider: str = typer.Option("google", help="OAuth provider"),
    return_path: str | None = typer.Option(None, "--return-path", help="Return path after OAuth"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Start OAuth flow and get the authorization URL."""
    set_json_mode(json_output)
    params: dict = {}
    if provider:
        params["provider"] = provider
    if return_path is not None:
        params["return_path"] = return_path

    resp = _api_request("get", f"{_NYLAS}/oauth/start", params=params)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(data.get("url", data))


@app.command("account")
def account(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """Get connected Nylas account details."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_NYLAS}/oauth/account")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    print_detail(data, [
        ("email", "Email"),
        ("provider", "Provider"),
        ("status", "Status"),
        ("connected_at", "Connected At"),
    ])


@app.command("org-accounts")
def org_accounts(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """List all connected accounts in the organization."""
    set_json_mode(json_output)
    resp = _api_request("get", f"{_NYLAS}/oauth/organization/accounts")

    data = resp.json()
    if json_output:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("accounts", [])
    print_table(
        items,
        [
            ("email", "Email"),
            ("provider", "Provider"),
            ("status", "Status"),
        ],
        title=f"Organization Accounts ({len(items)})",
    )


@app.command("disconnect")
def disconnect(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Disconnect Nylas account."""
    if not should_skip_confirm(yes):
        typer.confirm("Disconnect Nylas account?", abort=True)

    _api_request("post", f"{_NYLAS}/oauth/disconnect")

    rprint("[green]Disconnected[/green]")


@app.command("send")
def send(
    ctx: typer.Context,
    to: str = typer.Option(..., "--to", help="Recipient email address"),
    subject: str = typer.Option(..., "--subject", help="Email subject"),
    body: str = typer.Option(..., "--body", help="Email body"),
    reply_to_message_id: str | None = typer.Option(None, "--reply-to-message-id", help="Message ID to reply to"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Send an email via Nylas."""
    set_json_mode(json_output)
    payload = _build_body(to=to, subject=subject, body=body, reply_to_message_id=reply_to_message_id)

    resp = _api_request("post", f"{_NYLAS}/email/send", json=payload)

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint("[green]Email sent[/green]")


@app.command("update-signature")
def update_signature(
    ctx: typer.Context,
    signature: str = typer.Option(..., "--signature", help="Email signature (HTML or text)"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Update email signature."""
    set_json_mode(json_output)
    resp = _api_request("put", f"{_NYLAS}/email/account/signature", json={"signature": signature})

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint("[green]Signature updated[/green]")


@app.command("validate-signature")
def validate_signature(
    ctx: typer.Context,
    signature: str = typer.Option(..., "--signature", help="Email signature to validate"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Validate an email signature."""
    set_json_mode(json_output)
    resp = _api_request("post", f"{_NYLAS}/email/account/signature/validate", json={"signature": signature})

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(data)


@app.command("sync-thread")
def sync_thread(
    ctx: typer.Context,
    thread_id: str = typer.Argument(..., help="Thread ID to sync"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Sync messages for a thread from Nylas."""
    set_json_mode(json_output)
    resp = _api_request("post", f"{_NYLAS}/sync/threads/{thread_id}/sync")

    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"[green]Synced thread {thread_id}[/green]")


@app.command("download-attachment")
def download_attachment(
    ctx: typer.Context,
    message_id: str = typer.Argument(..., help="Message ID"),
    attachment_id: str = typer.Argument(..., help="Attachment ID"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Download an attachment from a message."""
    set_json_mode(json_output)
    from ac_cli.client import get_api_client

    with get_api_client() as client:
        resp = client.get(f"{_NYLAS}/sync/messages/{message_id}/attachments/{attachment_id}/download")
        resp.raise_for_status()

    if json_output:
        print_json({"status": "downloaded", "size": len(resp.content)})
        return

    if output:
        with open(output, "wb") as f:
            f.write(resp.content)
        rprint(f"[green]Saved to {output}[/green]")
    else:
        rprint(f"[green]Downloaded {len(resp.content)} bytes[/green]")

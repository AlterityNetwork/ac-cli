"""Nylas email integration commands."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import _api_request, _build_body, set_json_mode, should_skip_confirm
from ac_cli.formatting import print_detail, print_json, print_table

app = typer.Typer(help="Nylas email integration")

_NYLAS = "/api/v1/nylas"


@app.callback()
def nylas_callback(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_output
    set_json_mode(json_output)


@app.command("oauth-start")
def oauth_start(
    ctx: typer.Context,
    provider: str = typer.Option("google", help="OAuth provider"),
    return_path: str | None = typer.Option(None, "--return-path", help="Return path after OAuth"),
) -> None:
    """Start OAuth flow and get the authorization URL."""
    params: dict = {}
    if provider:
        params["provider"] = provider
    if return_path is not None:
        params["return_path"] = return_path

    resp = _api_request("get", f"{_NYLAS}/oauth/start", params=params)

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(data.get("url", data))


@app.command("account")
def account(
    ctx: typer.Context,
) -> None:
    """Get connected Nylas account details."""
    resp = _api_request("get", f"{_NYLAS}/oauth/account")

    data = resp.json()
    if ctx.obj["json"]:
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
) -> None:
    """List all connected accounts in the organization."""
    resp = _api_request("get", f"{_NYLAS}/oauth/organization/accounts")

    data = resp.json()
    if ctx.obj["json"]:
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
) -> None:
    """Send an email via Nylas."""
    payload = _build_body(to=to, subject=subject, body=body, reply_to_message_id=reply_to_message_id)

    resp = _api_request("post", f"{_NYLAS}/email/send", json=payload)

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint("[green]Email sent[/green]")


@app.command("update-signature")
def update_signature(
    ctx: typer.Context,
    signature: str = typer.Option(..., "--signature", help="Email signature (HTML or text)"),
) -> None:
    """Update email signature."""
    resp = _api_request("put", f"{_NYLAS}/email/account/signature", json={"signature": signature})

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint("[green]Signature updated[/green]")


@app.command("validate-signature")
def validate_signature(
    ctx: typer.Context,
    signature: str = typer.Option(..., "--signature", help="Email signature to validate"),
) -> None:
    """Validate an email signature."""
    resp = _api_request("post", f"{_NYLAS}/email/account/signature/validate", json={"signature": signature})

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(data)

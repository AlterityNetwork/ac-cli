"""Envoy dashboard command."""

import typer
from rich import print as rprint

from ac_cli.commands.crm import _api_request
from ac_cli.commands.envoy import _ENVOY
from ac_cli.formatting import print_json


def dashboard_command(
    ctx: typer.Context,
) -> None:
    """Show envoy outreach dashboard stats."""
    resp = _api_request("get", f"{_ENVOY}/dashboard/stats")

    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
        return

    rprint("\n[bold]Envoy Dashboard[/bold]\n")
    rprint(f"  Reply rate: {data.get('reply_rate', 0):.1%}")
    rprint(f"  Emails sent: {data.get('emails_sent', 0)}")
    rprint(f"  Meetings booked: {data.get('meetings_booked', 0)}")
    rprint(f"  Active sessions: {data.get('active_sessions', 0)}")
    rprint(f"  Ready for review: {data.get('ready_for_review', 0)}")

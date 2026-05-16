"""Envoy (outreach) commands: sequences, steps, recipients, outbox, dashboard."""

import typer

from ac_cli.commands._helpers import (  # noqa: F401
    JSON_OPTION,
    _api_request,
    _build_body,
    _handle_error,
    set_json_mode,
)

app = typer.Typer(help="Envoy outreach commands")

_ENVOY = "/api/v1/envoy"


@app.callback()
def envoy_callback(ctx: typer.Context) -> None:
    ctx.ensure_object(dict)


# -- Register sub-command groups from submodules ------------------------------

from ac_cli.commands.envoy.battlecards import battlecards_app  # noqa: E402
from ac_cli.commands.envoy.campaigns import campaigns_app  # noqa: E402
from ac_cli.commands.envoy.dashboard import dashboard_command  # noqa: E402
from ac_cli.commands.envoy.inbox import inbox_app  # noqa: E402
from ac_cli.commands.envoy.outbox import outbox_app  # noqa: E402
from ac_cli.commands.envoy.playbooks import playbooks_app  # noqa: E402
from ac_cli.commands.envoy.recipients import recipients_app  # noqa: E402
from ac_cli.commands.envoy.sequences import sequences_app  # noqa: E402
from ac_cli.commands.envoy.signals import signals_app  # noqa: E402
from ac_cli.commands.envoy.steps import steps_app  # noqa: E402

app.add_typer(sequences_app, name="sequences")
app.add_typer(campaigns_app, name="campaigns")
app.add_typer(battlecards_app, name="battlecards")
app.add_typer(playbooks_app, name="playbooks")
app.add_typer(steps_app, name="steps")
app.add_typer(recipients_app, name="recipients")
app.add_typer(outbox_app, name="outbox")
app.add_typer(inbox_app, name="inbox")
app.command("dashboard")(dashboard_command)
app.add_typer(signals_app, name="signals")


@app.command("inbox-count")
def inbox_count(
    ctx: typer.Context,
    json_output: bool = JSON_OPTION,
) -> None:
    """Get inbox thread count."""
    from rich import print as rprint

    from ac_cli.formatting import print_json

    set_json_mode(json_output)
    resp = _api_request("get", f"{_ENVOY}/dashboard/inbox-count")
    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(f"Inbox count: {data.get('count', data)}")

"""Envoy (outreach) commands: sequences, steps, recipients, outbox, dashboard."""

import typer

from ac_cli.commands._helpers import _api_request, _build_body, _handle_error  # noqa: F401

app = typer.Typer(help="Envoy outreach commands")

_ENVOY = "/api/v1/envoy"


@app.callback()
def envoy_callback(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_output


# -- Register sub-command groups from submodules ------------------------------

from ac_cli.commands.envoy.sequences import sequences_app  # noqa: E402
from ac_cli.commands.envoy.steps import steps_app  # noqa: E402
from ac_cli.commands.envoy.recipients import recipients_app  # noqa: E402
from ac_cli.commands.envoy.outbox import outbox_app  # noqa: E402
from ac_cli.commands.envoy.battlecards import battlecards_app  # noqa: E402
from ac_cli.commands.envoy.playbooks import playbooks_app  # noqa: E402
from ac_cli.commands.envoy.dashboard import dashboard_command  # noqa: E402
from ac_cli.commands.envoy.inbox import inbox_app  # noqa: E402
from ac_cli.commands.envoy.signals import signals_command  # noqa: E402

app.add_typer(sequences_app, name="sequences")
app.add_typer(battlecards_app, name="battlecards")
app.add_typer(playbooks_app, name="playbooks")
app.add_typer(steps_app, name="steps")
app.add_typer(recipients_app, name="recipients")
app.add_typer(outbox_app, name="outbox")
app.add_typer(inbox_app, name="inbox")
app.command("dashboard")(dashboard_command)
app.command("signals")(signals_command)


@app.command("inbox-count")
def inbox_count(ctx: typer.Context) -> None:
    """Get inbox thread count."""
    from ac_cli.commands._helpers import _api_request
    from ac_cli.formatting import print_json
    from rich import print as rprint

    resp = _api_request("get", f"{_ENVOY}/dashboard/inbox-count")
    data = resp.json()
    if ctx.obj["json"]:
        print_json(data)
    else:
        rprint(f"Inbox count: {data.get('count', data)}")

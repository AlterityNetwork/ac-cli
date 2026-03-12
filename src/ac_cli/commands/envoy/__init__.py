"""Envoy (outreach) commands: sequences, steps, recipients, outbox, dashboard."""

import typer

from ac_cli.commands.crm import _api_request, _build_body, _handle_error  # noqa: F401

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
from ac_cli.commands.envoy.dashboard import dashboard_command  # noqa: E402

app.add_typer(sequences_app, name="sequences")
app.add_typer(steps_app, name="steps")
app.add_typer(recipients_app, name="recipients")
app.add_typer(outbox_app, name="outbox")
app.command("dashboard")(dashboard_command)

"""Sequences commands: sequences, steps, recipients, outbox, dashboard."""

import typer

from ac_cli.commands._helpers import (  # noqa: F401
    JSON_OPTION,
    _api_request,
    _build_body,
    _handle_error,
    set_json_mode,
)

app = typer.Typer(help="Sequences commands")

_SEQUENCES = "/api/v1/sequences"


@app.callback()
def sequences_callback(ctx: typer.Context) -> None:
    ctx.ensure_object(dict)


# -- Register sub-command groups from submodules ------------------------------

from ac_cli.commands.sequences.battlecards import battlecards_app  # noqa: E402
from ac_cli.commands.sequences.dashboard import dashboard_command  # noqa: E402
from ac_cli.commands.sequences.inbox import inbox_app  # noqa: E402
from ac_cli.commands.sequences.outbox import outbox_app  # noqa: E402
from ac_cli.commands.sequences.playbooks import playbooks_app  # noqa: E402
from ac_cli.commands.sequences.recipients import recipients_app  # noqa: E402
from ac_cli.commands.sequences.sequences import sequences_app  # noqa: E402
from ac_cli.commands.sequences.signals import signals_app  # noqa: E402
from ac_cli.commands.sequences.steps import steps_app  # noqa: E402

app.add_typer(sequences_app, name="sequences")
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

    from ac_cli.formatting import as_text, print_json

    set_json_mode(json_output)
    resp = _api_request("get", f"{_SEQUENCES}/dashboard/inbox-count")
    data = resp.json()
    if json_output:
        print_json(data)
    else:
        rprint(as_text(f"Inbox count: {data.get('count', data)}"))

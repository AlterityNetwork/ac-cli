"""Launchpad commands: signal preferences."""

import typer

app = typer.Typer(help="Launchpad commands")

# -- Shared helpers -----------------------------------------------------------

_LAUNCHPAD = "/api/v1/launchpad"


@app.callback()
def launchpad_callback(ctx: typer.Context) -> None:
    ctx.ensure_object(dict)


# Sub-apps are imported after the prefix constant so the modules can import
# `_LAUNCHPAD` from this package without a circular-import failure.
from ac_cli.commands.launchpad.signal_preferences import (  # noqa: E402
    signal_preferences_app,
)

app.add_typer(signal_preferences_app, name="signal-preferences")

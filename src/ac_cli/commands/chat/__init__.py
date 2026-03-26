"""AI chat management commands."""

import typer

from ac_cli.commands._helpers import JSON_OPTION, _api_request, set_json_mode  # noqa: F401

app = typer.Typer(help="AI chat management")

_CHAT = "/api/v1/chat"


@app.callback()
def chat_callback(ctx: typer.Context) -> None:
    ctx.ensure_object(dict)


# -- Register sub-command groups from submodules ------------------------------

from ac_cli.commands.chat.threads import threads_app  # noqa: E402

app.add_typer(threads_app, name="threads")

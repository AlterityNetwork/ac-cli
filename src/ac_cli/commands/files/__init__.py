"""File management commands."""

import typer

from ac_cli.commands._helpers import _api_request, set_json_mode  # noqa: F401

app = typer.Typer(help="File management commands")

_FILES = "/api/v1/files"


@app.callback()
def files_callback(ctx: typer.Context) -> None:
    ctx.ensure_object(dict)


# -- Register sub-command groups from submodules ------------------------------

from ac_cli.commands.files.images import images_app  # noqa: E402

app.add_typer(images_app, name="images")

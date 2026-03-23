"""Workflow commands: runs, schedules, presets."""

import typer

from ac_cli.commands._helpers import _api_request, _build_body, _handle_error, set_json_mode  # noqa: F401

app = typer.Typer(help="Workflow commands")

_WORKFLOWS = "/api/v1/workflows"


@app.callback()
def workflows_callback(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_output
    set_json_mode(json_output)


# -- Register sub-command groups from submodules ------------------------------

from ac_cli.commands.workflows.runs import runs_app  # noqa: E402
from ac_cli.commands.workflows.schedules import schedules_app  # noqa: E402
from ac_cli.commands.workflows.presets import presets_app  # noqa: E402

app.add_typer(runs_app, name="runs")
app.add_typer(schedules_app, name="schedules")
app.add_typer(presets_app, name="presets")

"""Workflow commands: runs, schedules, presets, csv-parse."""

from __future__ import annotations

from pathlib import Path

import httpx
import typer
from rich import print as rprint

from ac_cli.client import get_api_client
from ac_cli.commands._helpers import (
    JSON_OPTION,
    _api_request,  # noqa: F401
    _build_body,  # noqa: F401
    _handle_error,
    set_json_mode,
)
from ac_cli.formatting import print_json, print_table

app = typer.Typer(help="Workflow commands")

_WORKFLOWS = "/api/v1/workflows"


@app.callback()
def workflows_callback(ctx: typer.Context) -> None:
    ctx.ensure_object(dict)


# -- Standalone commands -------------------------------------------------------


@app.command("csv-parse")
def csv_parse(
    ctx: typer.Context,
    file: str = typer.Argument(..., help="Path to CSV file"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Parse a CSV file into structured company data."""
    set_json_mode(json_output)
    path = Path(file)
    if not path.exists():
        rprint(f"[red]File not found:[/red] {file}")
        raise typer.Exit(code=1)

    if not path.suffix.lower() == ".csv":
        rprint("[red]File must be a .csv file[/red]")
        raise typer.Exit(code=1)

    # Multipart file upload — _api_request supports files= kwarg
    with open(path, "rb") as f:
        with get_api_client() as client:
            try:
                resp = client.post(
                    f"{_WORKFLOWS}/csv/parse-companies",
                    files={"file": (path.name, f, "text/csv")},
                )
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                _handle_error(exc)
            except httpx.HTTPError as exc:
                rprint(f"[red]Connection error:[/red] {exc}")
                raise typer.Exit(code=1)

    data = resp.json()
    if json_output:
        print_json(data)
        return

    companies = data.get("companies", [])
    rprint(
        f"\n[bold]Parsed {data.get('total_rows', 0)} rows[/bold]"
        f" (truncated: {data.get('truncated', False)})\n"
    )
    print_table(
        companies,
        [
            ("name", "Name"),
            ("website", "Website"),
            ("industry", "Industry"),
            ("location", "Location"),
            ("source_type", "Source"),
        ],
        title=f"Parsed Companies ({len(companies)})",
    )


# -- Register sub-command groups from submodules ------------------------------

from ac_cli.commands.workflows.runs import runs_app  # noqa: E402
from ac_cli.commands.workflows.schedules import schedules_app  # noqa: E402
from ac_cli.commands.workflows.presets import presets_app  # noqa: E402
from ac_cli.commands.workflows.run_companies import run_companies_app  # noqa: E402
from ac_cli.commands.workflows.run_people import run_people_app  # noqa: E402

app.add_typer(runs_app, name="runs")
app.add_typer(schedules_app, name="schedules")
app.add_typer(presets_app, name="presets")
app.add_typer(run_companies_app, name="run-companies")
app.add_typer(run_people_app, name="run-people")

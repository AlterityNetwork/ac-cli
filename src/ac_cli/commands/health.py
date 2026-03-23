"""Health-check command."""

from __future__ import annotations

import httpx
import typer
from rich import print as rprint

from ac_cli.commands._helpers import set_json_mode
from ac_cli.config import DEFAULT_API_URL, load_config
from ac_cli.formatting import print_json

app = typer.Typer(help="Service health commands")


@app.callback()
def health_callback(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_output
    set_json_mode(json_output)


@app.command("check")
def check(
    ctx: typer.Context,
    api_url: str | None = typer.Option(None, help="Override API URL"),
) -> None:
    """Check API health (no auth required)."""
    url = api_url or load_config().get("api_url", DEFAULT_API_URL)

    try:
        resp = httpx.get(f"{url}/health", timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as exc:
        if ctx.obj.get("json"):
            print_json({"error": True, "status_code": None, "detail": str(exc)})
        else:
            rprint(f"[red]Health check failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    if ctx.obj.get("json"):
        print_json(data)
        return

    rprint("[green]Service is healthy[/green]")
    for key, value in data.items():
        rprint(f"  {key}: {value}")

"""Health-check command."""

import httpx
import typer
from rich import print as rprint

from ac_cli.config import load_config

app = typer.Typer(help="Service health commands")

DEFAULT_API_URL = "http://localhost:8008"


@app.command("check")
def check(
    api_url: str | None = typer.Option(None, help="Override API URL"),
) -> None:
    """Check API health (no auth required)."""
    url = api_url or load_config().get("api_url", DEFAULT_API_URL)

    try:
        resp = httpx.get(f"{url}/health", timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as exc:
        rprint(f"[red]Health check failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    rprint("[green]Service is healthy[/green]")
    for key, value in data.items():
        rprint(f"  {key}: {value}")

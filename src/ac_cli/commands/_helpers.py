"""Shared helpers for CLI commands."""

import httpx
import typer
from rich import print as rprint

from ac_cli.client import get_api_client


def _handle_error(exc: httpx.HTTPStatusError) -> None:
    """Print API error detail and exit."""
    try:
        body = exc.response.json()
        detail = body.get("detail") or body.get("message") or exc.response.text
    except (ValueError, KeyError):
        detail = exc.response.text
    rprint(f"[red]Error {exc.response.status_code}:[/red] {detail}")
    raise typer.Exit(code=1)


def _api_request(method: str, path: str, **kwargs: object) -> httpx.Response:
    """Make an authenticated API request with standard error handling."""
    with get_api_client() as client:
        try:
            resp = getattr(client, method)(path, **kwargs)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)
        except httpx.HTTPError as exc:
            rprint(f"[red]Connection error:[/red] {exc}")
            raise typer.Exit(code=1)
    return resp


def _build_body(**fields: object) -> dict:
    """Build API request body from non-None fields."""
    body: dict = {}
    for key, value in fields.items():
        if value is not None:
            if key == "tags" and isinstance(value, str):
                body[key] = [t.strip() for t in value.split(",")]
            else:
                body[key] = value
    return body

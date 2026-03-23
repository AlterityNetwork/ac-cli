"""Shared helpers for CLI commands."""

import contextvars
import os

import httpx
import typer
from rich import print as rprint

from ac_cli.client import get_api_client
from ac_cli.formatting import print_json

_json_output: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "json_output", default=False
)

_EXIT_CODES = {401: 4, 403: 4, 404: 3, 409: 5, 422: 2}


def set_json_mode(enabled: bool) -> None:
    """Set the JSON output mode for the current context."""
    _json_output.set(enabled)


def should_skip_confirm(yes_flag: bool) -> bool:
    """Check if confirmation should be skipped via flag or AC_YES env var."""
    return yes_flag or os.environ.get("AC_YES", "").lower() in ("1", "true", "yes")


def _handle_error(exc: httpx.HTTPStatusError) -> None:
    """Print API error detail and exit."""
    try:
        body = exc.response.json()
        detail = body.get("detail") or body.get("message") or exc.response.text
    except (ValueError, KeyError):
        detail = exc.response.text
    exit_code = _EXIT_CODES.get(exc.response.status_code, 1)
    if _json_output.get():
        print_json({"error": True, "status_code": exc.response.status_code, "detail": detail})
    else:
        rprint(f"[red]Error {exc.response.status_code}:[/red] {detail}")
    raise typer.Exit(code=exit_code)


def _api_request(method: str, path: str, **kwargs: object) -> httpx.Response:
    """Make an authenticated API request with standard error handling."""
    with get_api_client() as client:
        try:
            resp = getattr(client, method)(path, **kwargs)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _handle_error(exc)
        except httpx.HTTPError as exc:
            if _json_output.get():
                print_json({"error": True, "status_code": None, "detail": str(exc)})
            else:
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

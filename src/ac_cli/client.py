"""Authenticated httpx client for the AgencyCore API."""

import httpx
import typer

from ac_cli.config import load_config


def get_api_client() -> httpx.Client:
    """Return an httpx.Client with base URL and auth header from stored config.

    Raises typer.Exit if not logged in.
    """
    cfg = load_config()
    access_token = cfg.get("access_token")
    api_url = cfg.get("api_url")

    if not access_token or not api_url:
        typer.echo("Not logged in. Run `ac login` first.")
        raise typer.Exit(code=1)

    return httpx.Client(
        base_url=api_url,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30.0,
    )

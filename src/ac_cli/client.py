"""Authenticated httpx client for the AgencyCore API."""

import os

import httpx
import typer

from ac_cli.config import load_config, save_config

ACT_AS_ENV_VAR = "AC_ACT_AS"
ACT_AS_HEADER = "X-Act-As-User"


def _refresh_access_token(cfg: dict) -> str:
    """Use stored refresh_token to obtain a new access_token from Supabase.

    Persists the new tokens to config. Returns the new access_token.
    Raises typer.Exit on failure.
    """
    from supabase import AuthApiError, create_client

    supabase_url = cfg.get("supabase_url")
    supabase_anon_key = cfg.get("supabase_anon_key")
    refresh_token = cfg.get("refresh_token")

    if not supabase_url or not supabase_anon_key or not refresh_token:
        from ac_cli.config import get_active_env

        env = get_active_env()
        typer.echo(
            f"Session expired. Run `ac login --env {env}` to re-authenticate."
        )
        raise typer.Exit(code=1)

    try:
        sb = create_client(supabase_url, supabase_anon_key)
        response = sb.auth.refresh_session(refresh_token)
    except (httpx.HTTPError, AuthApiError, ValueError, KeyError) as exc:
        typer.echo(f"Token refresh failed: {exc}\nRun `ac login` to re-authenticate.")
        raise typer.Exit(code=1) from exc

    session = response.session
    if not session:
        typer.echo("Token refresh returned no session. Run `ac login` to re-authenticate.")
        raise typer.Exit(code=1)

    cfg["access_token"] = session.access_token
    cfg["refresh_token"] = session.refresh_token
    save_config(cfg)
    return session.access_token


class _AuthClient(httpx.Client):
    """httpx.Client that auto-refreshes expired Supabase tokens on 401."""

    def __init__(self, cfg: dict, **kwargs: object) -> None:
        self._cfg = cfg
        super().__init__(**kwargs)

    def send(self, request: httpx.Request, **kwargs: object) -> httpx.Response:
        response = super().send(request, **kwargs)

        if response.status_code == 401:
            new_token = _refresh_access_token(self._cfg)
            request.headers["Authorization"] = f"Bearer {new_token}"
            self.headers["Authorization"] = f"Bearer {new_token}"
            response = super().send(request, **kwargs)

        return response


def get_api_client() -> httpx.Client:
    """Return an httpx.Client with base URL and auth header from stored config.

    The client auto-refreshes the Supabase access token on 401 responses.
    Raises typer.Exit if not logged in.
    """
    cfg = load_config()
    access_token = cfg.get("access_token")
    api_url = cfg.get("api_url")

    if not access_token or not api_url:
        typer.echo("Not logged in. Run `ac login` first.")
        raise typer.Exit(code=1)

    headers = {"Authorization": f"Bearer {access_token}"}
    act_as = os.environ.get(ACT_AS_ENV_VAR, "").strip()
    if act_as:
        headers[ACT_AS_HEADER] = act_as

    return _AuthClient(
        cfg=cfg,
        base_url=api_url,
        headers=headers,
        timeout=30.0,
        follow_redirects=True,
    )

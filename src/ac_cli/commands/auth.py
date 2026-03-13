"""Authentication commands: login, logout, whoami."""

import httpx
import typer
from rich import print as rprint
from supabase import create_client

from ac_cli.client import get_api_client
from ac_cli.config import (
    DEV_API_URL,
    DEV_SUPABASE_ANON_KEY,
    DEV_SUPABASE_URL,
    STAGING_API_URL,
    STAGING_SUPABASE_ANON_KEY,
    STAGING_SUPABASE_URL,
    clear_config,
    save_config,
)

app = typer.Typer(help="Authentication commands")


@app.command()
def login(
    email: str = typer.Option(None, help="Supabase account email"),
    password: str = typer.Option(None, help="Account password"),
    supabase_url: str = typer.Option(None, help="Supabase project URL"),
    supabase_anon_key: str = typer.Option(None, help="Supabase anonymous/public key"),
    api_url: str = typer.Option(None, help="AgencyCore API base URL"),
    dev: bool = typer.Option(False, "--dev", help="Use local dev environment (localhost)"),
) -> None:
    """Sign in with email and password via Supabase.

    By default, connects to the staging environment. Pass --dev to use local
    dev services (localhost API + local Supabase).
    """
    if dev:
        api_url = api_url or DEV_API_URL
        supabase_url = supabase_url or DEV_SUPABASE_URL
        supabase_anon_key = supabase_anon_key or DEV_SUPABASE_ANON_KEY
        rprint("[dim]Using local dev environment[/dim]")
    else:
        api_url = api_url or STAGING_API_URL
        supabase_url = supabase_url or STAGING_SUPABASE_URL
        supabase_anon_key = supabase_anon_key or STAGING_SUPABASE_ANON_KEY

    if not email:
        email = typer.prompt("Email")
    if not password:
        password = typer.prompt("Password", hide_input=True)

    try:
        client = create_client(supabase_url, supabase_anon_key)
        response = client.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
    except Exception as exc:
        rprint(f"[red]Login failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    session = response.session
    if not session:
        rprint("[red]Login failed: no session returned.[/red]")
        raise typer.Exit(code=1)

    save_config(
        {
            "api_url": api_url,
            "supabase_url": supabase_url,
            "supabase_anon_key": supabase_anon_key,
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
        }
    )
    rprint(f"[green]Logged in as {email}[/green]")


@app.command()
def logout() -> None:
    """Clear stored credentials."""
    clear_config()
    rprint("[green]Logged out.[/green]")


@app.command()
def whoami() -> None:
    """Show the currently authenticated user."""
    with get_api_client() as client:
        try:
            resp = client.get("/whoami")
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            try:
                detail = exc.response.json().get("detail", exc.response.text)
            except Exception:
                detail = exc.response.text
            rprint(f"[red]Error {exc.response.status_code}:[/red] {detail}")
            raise typer.Exit(code=1)
        except httpx.HTTPError as exc:
            rprint(f"[red]Connection error:[/red] {exc}")
            raise typer.Exit(code=1)
    rprint(resp.json())

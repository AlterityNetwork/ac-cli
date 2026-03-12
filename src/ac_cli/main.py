"""AgencyCore CLI entry point."""

import typer

from ac_cli.commands import auth, crm, health

app = typer.Typer(
    name="ac",
    help="AgencyCore CLI — authenticate and interact with the AgencyCore API.",
    no_args_is_help=True,
)

# Register sub-command groups
app.add_typer(auth.app, name="auth")
app.add_typer(crm.app, name="crm")
app.add_typer(health.app, name="health")

# Promote common auth commands to top level for convenience
app.command("login")(auth.login)
app.command("logout")(auth.logout)
app.command("whoami")(auth.whoami)

if __name__ == "__main__":
    app()

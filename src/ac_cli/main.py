"""AgencyCore CLI entry point."""

import os

import typer

from ac_cli import __version__
from ac_cli.client import ACT_AS_ENV_VAR
from ac_cli.commands import (
    admin,
    apps,
    auth,
    chat,
    crm,
    env,
    envoy,
    files,
    health,
    hooks,
    legal_documents,
    managed_onboarding,
    marketplace,
    messaging,
    network,
    notifications,
    nylas,
    profiles,
    resources,
    tos,
    workflows,
    writing_styles,
)
from ac_cli.formatting import OutputMode, set_output_mode


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"ac {__version__}")
        raise typer.Exit()


app = typer.Typer(
    name="ac",
    help="AgencyCore CLI — authenticate and interact with the AgencyCore API.",
    no_args_is_help=True,
)


@app.callback()
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show version and exit",
        callback=_version_callback,
        is_eager=True,
    ),
    act_as: str = typer.Option(
        None,
        "--act-as",
        help=(
            "Superadmin only: act on behalf of the user with this ID. "
            "Equivalent to setting AC_ACT_AS=<user-id>. Every request adds "
            "X-Act-As-User and is audit-logged server-side."
        ),
        envvar=ACT_AS_ENV_VAR,
    ),
    output: OutputMode = typer.Option(
        OutputMode.table,
        "--output",
        "-o",
        help="Output format",
        case_sensitive=False,
    ),
) -> None:
    ctx.obj = ctx.obj or {}
    set_output_mode(output)
    if act_as:
        os.environ[ACT_AS_ENV_VAR] = act_as.strip()


# Register sub-command groups
app.add_typer(admin.app, name="admin")
app.add_typer(apps.app, name="apps")
app.add_typer(auth.app, name="auth")
app.add_typer(chat.app, name="chat")
app.add_typer(crm.app, name="crm")
app.add_typer(env.app, name="env")
app.add_typer(health.app, name="health")
app.add_typer(envoy.app, name="envoy")
app.add_typer(files.app, name="files")
app.add_typer(hooks.app, name="hooks")
app.add_typer(legal_documents.app, name="legal-docs")
app.add_typer(managed_onboarding.app, name="onboarding")
app.add_typer(marketplace.app, name="marketplace")
app.add_typer(messaging.app, name="messaging")
app.add_typer(network.app, name="network")
app.add_typer(notifications.app, name="notifications")
app.add_typer(nylas.app, name="nylas")
app.add_typer(profiles.app, name="profiles")
app.add_typer(resources.app, name="resources")
app.add_typer(tos.app, name="tos")
app.add_typer(workflows.app, name="workflows")
app.add_typer(writing_styles.app, name="styles")

# Promote common auth commands to top level for convenience
app.command("login")(auth.login)
app.command("logout")(auth.logout)
app.command("whoami")(auth.whoami)

if __name__ == "__main__":
    app()

"""Admin commands: users, organizations, queues, demo."""

import typer
from rich import print as rprint

from ac_cli.commands._helpers import _api_request, _build_body, _handle_error, set_json_mode  # noqa: F401

app = typer.Typer(help="Admin commands (super admin only)")

_ADMIN = "/api/v1/admin"


@app.callback()
def admin_callback(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_output
    set_json_mode(json_output)


# -- Register sub-command groups from submodules ------------------------------

from ac_cli.commands.admin.users import users_app  # noqa: E402
from ac_cli.commands.admin.organizations import organizations_app  # noqa: E402
from ac_cli.commands.admin.queues import queues_app  # noqa: E402
from ac_cli.commands.admin.demo import demo_app  # noqa: E402
from ac_cli.commands.admin.onboarding import onboarding_app  # noqa: E402
from ac_cli.commands.admin.app_usage import app_usage_app  # noqa: E402
from ac_cli.commands.admin.ai_usage import ai_usage_app  # noqa: E402

app.add_typer(users_app, name="users")
app.add_typer(organizations_app, name="orgs")
app.add_typer(queues_app, name="queues")
app.add_typer(demo_app, name="demo")
app.add_typer(onboarding_app, name="onboarding")
app.add_typer(app_usage_app, name="app-usage")
app.add_typer(ai_usage_app, name="ai-usage")

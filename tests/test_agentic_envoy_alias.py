"""ENG-2992: `ac agentic outreach` is the group, and `ac agentic envoy` a hidden alias.

The CLI is on PyPI, so a script or an agent can still call the old name.
"""

from typer.testing import CliRunner

from ac_cli.main import app


def test_ac_agentic_outreach_runs(invoke, mock_api):
    route = mock_api.get("/api/v1/agentic/outreach/campaigns").respond(200, json={"items": []})
    result = invoke(["agentic", "outreach", "campaigns", "list"])
    assert result.exit_code == 0, result.output
    assert route.called


def test_ac_agentic_envoy_still_runs_on_the_outreach_routes(invoke, mock_api):
    route = mock_api.get("/api/v1/agentic/outreach/campaigns").respond(200, json={"items": []})
    result = invoke(["agentic", "envoy", "campaigns", "list"])
    assert result.exit_code == 0, result.output
    assert route.called


def test_help_lists_outreach_and_hides_envoy():
    result = CliRunner().invoke(app, ["agentic", "--help"])
    assert result.exit_code == 0, result.output
    assert "outreach" in result.output
    assert "envoy" not in result.output.lower()

"""ENG-2990: `ac envoy` is gone. The Sequences commands answer only on `ac sequences`."""

from typer.testing import CliRunner

from ac_cli.main import app


def test_ac_envoy_is_not_a_command(invoke, mock_api):
    route = mock_api.get("/api/v1/sequences/dashboard/inbox-count").respond(200, json={"count": 7})
    result = invoke(["envoy", "inbox-count"])
    assert result.exit_code != 0
    assert not route.called


def test_help_lists_sequences_and_not_envoy():
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "sequences" in result.output
    assert "envoy" not in result.output.lower()

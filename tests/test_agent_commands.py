"""Tests for the ac agent command group."""

import json

import pytest


class TestAgentCommands:
    """Verify 'ac agent commands' returns valid JSON command tree."""

    def test_outputs_json(self, invoke, mock_api):
        result = invoke(["agent", "commands"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) > 0

    def test_domain_filter(self, invoke, mock_api):
        result = invoke(["agent", "commands", "--domain", "crm"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert all(e["path"].startswith("crm") for e in data)

    def test_pretty_flag(self, invoke, mock_api):
        result = invoke(["agent", "commands", "--pretty"])
        assert result.exit_code == 0
        # Pretty output has indentation
        assert "  " in result.output
        data = json.loads(result.output)
        assert isinstance(data, list)


class TestAgentHelp:
    """Verify 'ac agent help' returns command schema."""

    def test_valid_command(self, invoke, mock_api):
        result = invoke(["agent", "help", "crm companies list"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["path"] == "crm companies list"
        assert "params" in data

    def test_dotted_path(self, invoke, mock_api):
        result = invoke(["agent", "help", "crm.companies.list"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["path"] == "crm companies list"

    def test_nonexistent_command(self, invoke, mock_api):
        result = invoke(["agent", "help", "nonexistent.command"])
        assert result.exit_code == 3
        data = json.loads(result.output)
        assert data["error"] is True


class TestFieldFiltering:
    """Verify --fields client-side filtering."""

    def test_filter_fields_in_list(self):
        from ac_cli.commands.agent import _filter_fields

        data = {"data": [{"id": "1", "name": "Acme", "industry": "SaaS"}]}
        result = _filter_fields(data, ["id", "name"])
        assert result["data"] == [{"id": "1", "name": "Acme"}]

    def test_filter_fields_no_fields(self):
        from ac_cli.commands.agent import _filter_fields

        data = {"id": "1", "name": "Acme"}
        result = _filter_fields(data, [])
        assert result == data

    def test_filter_fields_on_flat_dict(self):
        from ac_cli.commands.agent import _filter_fields

        data = {"id": "1", "name": "Acme", "industry": "SaaS"}
        result = _filter_fields(data, ["id", "name"])
        assert result == {"id": "1", "name": "Acme"}

    def test_filter_fields_on_list(self):
        from ac_cli.commands.agent import _filter_fields

        data = [{"id": "1", "name": "Acme", "x": "y"}]
        result = _filter_fields(data, ["id", "name"])
        assert result == [{"id": "1", "name": "Acme"}]


class TestMakeEnvelope:
    """Verify the consistent envelope helper."""

    def test_success_envelope(self):
        from ac_cli.commands.agent import _make_envelope

        env = _make_envelope(ok=True, command="test", data={"id": 1}, duration_ms=42)
        assert env["ok"] is True
        assert env["command"] == "test"
        assert env["data"] == {"id": 1}
        assert env["duration_ms"] == 42

    def test_error_envelope(self):
        from ac_cli.commands.agent import _make_envelope

        env = _make_envelope(ok=False, command="test", error="Not found")
        assert env["ok"] is False
        assert env["error"] == "Not found"
        assert "data" not in env

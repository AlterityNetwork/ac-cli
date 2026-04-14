"""Tests for the SDK command registry."""

from ac_cli.main import app
from ac_cli.sdk.registry import build_registry, get_command_schema


class TestBuildRegistry:
    """Verify registry returns a complete command tree."""

    def test_returns_list(self):
        registry = build_registry(app)
        assert isinstance(registry, list)
        assert len(registry) > 0

    def test_all_entries_have_required_fields(self):
        registry = build_registry(app)
        for entry in registry:
            assert "path" in entry
            assert "full_command" in entry
            assert "mode" in entry
            assert "params" in entry
            assert entry["mode"] in ("read", "write")

    def test_crm_companies_list_exists(self):
        registry = build_registry(app)
        paths = [e["path"] for e in registry]
        assert "crm companies list" in paths

    def test_crm_companies_create_is_write(self):
        registry = build_registry(app)
        for entry in registry:
            if entry["path"] == "crm companies create":
                assert entry["mode"] == "write"
                return
        pytest.fail("crm companies create not found in registry")

    def test_crm_companies_list_is_read(self):
        registry = build_registry(app)
        for entry in registry:
            if entry["path"] == "crm companies list":
                assert entry["mode"] == "read"
                return
        pytest.fail("crm companies list not found in registry")

    def test_params_extracted(self):
        registry = build_registry(app)
        for entry in registry:
            if entry["path"] == "crm companies list":
                param_names = [p["name"] for p in entry["params"]]
                assert "limit" in param_names
                assert "offset" in param_names
                return
        pytest.fail("crm companies list not found")

    def test_all_major_groups_present(self):
        registry = build_registry(app)
        paths = [e["path"] for e in registry]
        groups = {p.split()[0] for p in paths}
        assert "crm" in groups
        assert "envoy" in groups
        assert "admin" in groups
        assert "workflows" in groups

    def test_full_command_includes_ac_prefix(self):
        registry = build_registry(app)
        for entry in registry:
            assert entry["full_command"].startswith("ac ")


class TestGetCommandSchema:
    """Verify single-command schema lookup."""

    def test_spaced_path(self):
        schema = get_command_schema(app, "crm companies list")
        assert schema is not None
        assert schema["path"] == "crm companies list"

    def test_dotted_path(self):
        schema = get_command_schema(app, "crm.companies.list")
        assert schema is not None
        assert schema["path"] == "crm companies list"

    def test_nonexistent_returns_none(self):
        schema = get_command_schema(app, "nonexistent.command")
        assert schema is None

    def test_schema_has_params(self):
        schema = get_command_schema(app, "crm.companies.create")
        assert schema is not None
        assert len(schema["params"]) > 0
        param_names = [p["name"] for p in schema["params"]]
        assert "name" in param_names


import pytest  # noqa: E402

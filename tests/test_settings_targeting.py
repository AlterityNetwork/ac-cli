"""The targeting command uses the copilot-safe endpoint."""

import json
from pathlib import Path

import pytest


@pytest.mark.parametrize("json_mode", [False, True])
def test_set_targeting(invoke, mock_api, tmp_path, json_mode):
    mock_api.get("/whoami").respond(200, json={"organization_id": "org-456"})
    path = tmp_path / "icps.json"
    profiles = [{"name": "Agencies", "description": "UK agencies", "country_codes": ["GB"]}]
    path.write_text(json.dumps(profiles))
    route = mock_api.patch("/api/v1/organizations/org-456/targeting").respond(
        200, json={"ideal_customer_profiles": profiles}
    )
    result = invoke(
        ["settings", "targeting", "set", "--profiles-file", str(path)]
        + (["--json"] if json_mode else [])
    )
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == {"ideal_customer_profiles": profiles}
    if json_mode:
        assert json.loads(result.output)["ideal_customer_profiles"] == profiles


@pytest.mark.parametrize("value", ["not json", "{}"])
def test_rejects_invalid_file(invoke, tmp_path, value):
    path = tmp_path / "icps.json"
    path.write_text(value)
    result = invoke(["settings", "targeting", "set", "--profiles-file", str(path)])
    assert result.exit_code == 2
    assert "JSON array" in result.output


def test_targeting_permission_error(invoke, mock_api, tmp_path):
    mock_api.get("/whoami").respond(200, json={"organization_id": "org-456"})
    path = tmp_path / "icps.json"
    path.write_text("[]")
    mock_api.patch("/api/v1/organizations/org-456/targeting").respond(
        403, json={"detail": "Forbidden"}
    )
    result = invoke(["settings", "targeting", "set", "--profiles-file", str(path), "--json"])
    assert result.exit_code == 4
    assert json.loads(result.output)["status_code"] == 403


@pytest.mark.parametrize("value", ["not json", "{}", None])
def test_targeting_invalid_file_is_json_error(invoke, tmp_path, value):
    path = tmp_path / "icps.json"
    if value is not None:
        path.write_text(value)
    result = invoke(["settings", "targeting", "set", "--profiles-file", str(path), "--json"])
    assert result.exit_code == 2
    assert json.loads(result.output) == {
        "error": True,
        "status_code": None,
        "detail": "--profiles-file must contain a JSON array",
    }


@pytest.mark.parametrize("admin", [False, True])
def test_targeting_preserves_utf8_on_non_utf8_locale(
    invoke, mock_api, tmp_path, monkeypatch, admin
):
    profiles = [{"name": "Agences françaises", "description": "Équipes à Paris"}]
    path = tmp_path / "icps.json"
    path.write_text(json.dumps(profiles, ensure_ascii=False), encoding="utf-8")
    read_text = Path.read_text

    def locale_read_text(self, encoding=None, errors=None):
        return read_text(self, encoding=encoding or "cp1252", errors=errors)

    monkeypatch.setattr(Path, "read_text", locale_read_text)
    if admin:
        endpoint = "/api/v1/admin/organizations/org-456"
        command = ["admin", "orgs", "update", "org-456", "--icps-file", str(path)]
    else:
        mock_api.get("/whoami").respond(200, json={"organization_id": "org-456"})
        endpoint = "/api/v1/organizations/org-456/targeting"
        command = ["settings", "targeting", "set", "--profiles-file", str(path)]
    route = mock_api.patch(endpoint).respond(200, json={"ideal_customer_profiles": profiles})
    result = invoke(command + ["--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content)["ideal_customer_profiles"] == profiles

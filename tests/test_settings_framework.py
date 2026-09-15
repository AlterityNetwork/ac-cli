"""Tests for `ac settings framework` (the copilot approval framework)."""

import json

_BASE = "/api/v1/settings/framework"

SAMPLE = {
    "id": "fw-1",
    "organization_id": "org-456",
    "content_md": "# Rules\n\nApprove replies.",
    "published_content_md": None,
    "status": "draft",
    "published_by": None,
    "published_by_name": None,
    "published_at": None,
    "updated_by": "user-123",
    "updated_by_name": "Cora Pilot",
    "updated_at": "2026-09-14T10:00:00+00:00",
    "is_template": False,
}


def test_framework_get(invoke, mock_api):
    mock_api.get(_BASE).respond(200, json=SAMPLE)
    result = invoke(["settings", "framework", "get"])
    assert result.exit_code == 0
    assert "draft" in result.output
    assert "Approve replies." in result.output


def test_framework_get_json(invoke, mock_api):
    mock_api.get(_BASE).respond(200, json=SAMPLE)
    result = invoke(["settings", "framework", "get", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["content_md"].startswith("# Rules")


def test_framework_get_template(invoke, mock_api):
    mock_api.get(_BASE).respond(200, json={**SAMPLE, "id": None, "is_template": True})
    result = invoke(["settings", "framework", "get"])
    assert result.exit_code == 0
    assert "template" in result.output.lower()


def test_framework_set_from_content(invoke, mock_api):
    route = mock_api.put(_BASE).respond(200, json={**SAMPLE, "content_md": "# New"})
    result = invoke(["settings", "framework", "set", "--content", "# New"])
    assert result.exit_code == 0
    assert json.loads(route.calls.last.request.content) == {"content_md": "# New"}
    assert "Draft saved" in result.output


def test_framework_set_from_file(invoke, mock_api, tmp_path):
    path = tmp_path / "framework.md"
    path.write_text("# From file\n")
    route = mock_api.put(_BASE).respond(200, json={**SAMPLE, "content_md": "# From file\n"})
    result = invoke(["settings", "framework", "set", "--content-file", str(path)])
    assert result.exit_code == 0
    assert json.loads(route.calls.last.request.content) == {"content_md": "# From file\n"}


def test_framework_set_requires_one_source(invoke, mock_api):
    result = invoke(["settings", "framework", "set"])
    assert result.exit_code != 0
    assert "--content" in result.output


def test_framework_set_rejects_both_sources(invoke, mock_api, tmp_path):
    path = tmp_path / "framework.md"
    path.write_text("# x")
    result = invoke(
        ["settings", "framework", "set", "--content", "# y", "--content-file", str(path)]
    )
    assert result.exit_code != 0


def test_framework_publish_stored_draft(invoke, mock_api):
    published = {
        **SAMPLE,
        "status": "published",
        "published_content_md": SAMPLE["content_md"],
        "published_by_name": "Cora Pilot",
        "published_at": "2026-09-14T12:00:00+00:00",
    }
    route = mock_api.post(f"{_BASE}/publish").respond(200, json=published)
    result = invoke(["settings", "framework", "publish"])
    assert result.exit_code == 0
    assert json.loads(route.calls.last.request.content) == {}
    assert "Published" in result.output
    assert "Cora Pilot" in result.output


def test_framework_publish_with_content_json(invoke, mock_api):
    published = {**SAMPLE, "status": "published", "published_content_md": "# Final"}
    route = mock_api.post(f"{_BASE}/publish").respond(200, json=published)
    result = invoke(["settings", "framework", "publish", "--content", "# Final", "--json"])
    assert result.exit_code == 0
    assert json.loads(route.calls.last.request.content) == {"content_md": "# Final"}
    assert json.loads(result.output)["status"] == "published"


def test_framework_publish_forbidden(invoke, mock_api):
    mock_api.post(f"{_BASE}/publish").respond(403, json={"detail": {"code": "insufficient_role"}})
    result = invoke(["settings", "framework", "publish"])
    assert result.exit_code == 4


def test_framework_preserves_markup_in_names(invoke, mock_api):
    mock_api.get(_BASE).respond(
        200,
        json={**SAMPLE, "published_at": "2026-09-15", "published_by_name": "Cora [/unexpected]"},
    )
    result = invoke(["settings", "framework", "get"])
    assert result.exit_code == 0, result.output
    assert "Cora [/unexpected]" in result.output


def test_framework_missing_content_is_json_error(invoke):
    result = invoke(["settings", "framework", "set", "--json"])
    assert result.exit_code == 2
    assert json.loads(result.output) == {
        "error": True,
        "status_code": None,
        "detail": "Provide --content or --content-file",
    }


def test_framework_conflicting_content_is_json_error(invoke, tmp_path):
    path = tmp_path / "framework.md"
    path.write_text("rules")
    result = invoke(
        [
            "settings",
            "framework",
            "publish",
            "--content",
            "rules",
            "--content-file",
            str(path),
            "--json",
        ]
    )
    assert result.exit_code == 2
    assert (
        json.loads(result.output)["detail"] == "--content and --content-file are mutually exclusive"
    )


def test_framework_missing_file_is_json_error(invoke, tmp_path):
    result = invoke(
        ["settings", "framework", "set", "--content-file", str(tmp_path / "absent"), "--json"]
    )
    assert result.exit_code == 2
    assert json.loads(result.output)["status_code"] is None

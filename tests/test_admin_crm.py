"""Tests for admin CRM hard-delete commands."""

import json


def test_hard_delete_company_with_yes(invoke, mock_api):
    mock_api.delete("/api/v1/admin/crm/companies/c-1/hard").respond(204)
    result = invoke(["admin", "crm", "hard-delete-company", "c-1", "--yes"])
    assert result.exit_code == 0
    assert "Hard-deleted company c-1" in result.output


def test_hard_delete_company_json(invoke, mock_api):
    mock_api.delete("/api/v1/admin/crm/companies/c-1/hard").respond(204)
    result = invoke(["admin", "crm", "hard-delete-company", "c-1", "--yes", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output) == {
        "ok": True,
        "id": "c-1",
        "action": "hard-delete-company",
    }


def test_hard_delete_company_aborted(invoke, mock_api):
    result = invoke(["admin", "crm", "hard-delete-company", "c-1"], input="n\n")
    assert result.exit_code == 1


def test_hard_delete_company_forbidden(invoke, mock_api):
    mock_api.delete("/api/v1/admin/crm/companies/c-1/hard").respond(
        403, json={"detail": "forbidden"}
    )
    result = invoke(["admin", "crm", "hard-delete-company", "c-1", "--yes"])
    assert result.exit_code == 4


def test_hard_delete_person_with_yes(invoke, mock_api):
    mock_api.delete("/api/v1/admin/crm/people/p-1/hard").respond(204)
    result = invoke(["admin", "crm", "hard-delete-person", "p-1", "--yes"])
    assert result.exit_code == 0
    assert "Hard-deleted person p-1" in result.output


def test_hard_delete_person_aborted(invoke, mock_api):
    result = invoke(["admin", "crm", "hard-delete-person", "p-1"], input="n\n")
    assert result.exit_code == 1

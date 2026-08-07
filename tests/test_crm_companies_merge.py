"""Tests for CRM company merge commands (ENG-1963, ENG-1964).

Every case asserts the REQUEST the CLI actually sent, not just the exit code —
a mocked response proves nothing about whether the command talks to the API
correctly.
"""

import json

A = "aaaaaaaa-0000-0000-0000-000000000001"
B = "aaaaaaaa-0000-0000-0000-000000000002"

_CANDIDATES = "/api/v1/crm/companies/merge/candidates"
_PREVIEW = "/api/v1/crm/companies/merge/preview"
_MERGE = "/api/v1/crm/companies/merge"

GROUP = {
    "company_ids": [A, B],
    "match_reasons": ["linkedin"],
    "companies": [
        {
            "id": A,
            "name": "Acme",
            "linkedin_url": "https://www.linkedin.com/company/acme",
            "normalized_domain": "acme.com",
            "deleted_at": None,
        },
        {
            "id": B,
            "name": "Acme Holdings",
            "linkedin_url": "https://www.linkedin.com/company/acme",
            "normalized_domain": "acme.com",
            "deleted_at": "2026-01-01T00:00:00Z",
        },
    ],
}

CANDIDATES_RESPONSE = {
    "data": [GROUP],
    "total": 1,
    "limit": 50,
    "offset": 0,
    "has_more": False,
}

PREVIEW_RESPONSE = {
    "survivor_id": A,
    "company_ids": [A, B],
    "companies": GROUP["companies"],
    "fields": [
        {
            "field": "name",
            "values": {A: "Acme", B: "Acme Holdings"},
            "survivor_value": "Acme",
            "conflict": True,
            "fillable": False,
        }
    ],
    "reference_counts": [
        {"company_id": A, "counts": {"crm_activities": 0}},
        {"company_id": B, "counts": {"crm_activities": 9}},
    ],
    "plan": [{"table": "crm_activities", "repoint": 9, "drop": 0}],
    "already_merged": [],
}

MERGE_RESPONSE = {
    "survivor_id": A,
    "merged": [B],
    "already_merged": [],
    "field_updates": {},
}


# ---------------------------------------------------------------------------
# candidates
# ---------------------------------------------------------------------------


def test_candidates_lists_groups(invoke, mock_api):
    mock_api.get(_CANDIDATES).respond(200, json=CANDIDATES_RESPONSE)
    result = invoke(["crm", "companies", "merge", "candidates"])
    assert result.exit_code == 0
    assert "Acme" in result.output


def test_candidates_omits_include_deleted_by_default(invoke, mock_api):
    """Off by default, or every soft-deleted company reads as a duplicate."""
    route = mock_api.get(_CANDIDATES).respond(200, json=CANDIDATES_RESPONSE)
    result = invoke(["crm", "companies", "merge", "candidates"])
    assert result.exit_code == 0
    assert "include_deleted" not in route.calls.last.request.url.params


def test_candidates_forwards_include_deleted(invoke, mock_api):
    route = mock_api.get(_CANDIDATES).respond(200, json=CANDIDATES_RESPONSE)
    result = invoke(["crm", "companies", "merge", "candidates", "--include-deleted"])
    assert result.exit_code == 0
    assert route.calls.last.request.url.params.get("include_deleted") == "true"


def test_candidates_marks_the_tombstone(invoke, mock_api):
    """The operator has to see which member is deleted before choosing a
    survivor."""
    mock_api.get(_CANDIDATES).respond(200, json=CANDIDATES_RESPONSE)
    result = invoke(["crm", "companies", "merge", "candidates", "--include-deleted"])
    assert result.exit_code == 0
    assert "deleted" in result.output
    assert "live" in result.output


def test_candidates_forwards_kinds(invoke, mock_api):
    route = mock_api.get(_CANDIDATES).respond(200, json=CANDIDATES_RESPONSE)
    result = invoke(["crm", "companies", "merge", "candidates", "--kind", "linkedin"])
    assert result.exit_code == 0
    assert route.calls.last.request.url.params.get_list("kinds") == ["linkedin"]


def test_candidates_json(invoke, mock_api):
    mock_api.get(_CANDIDATES).respond(200, json=CANDIDATES_RESPONSE)
    result = invoke(["crm", "companies", "merge", "candidates", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["total"] == 1


def test_candidates_empty(invoke, mock_api):
    mock_api.get(_CANDIDATES).respond(
        200, json={"data": [], "total": 0, "limit": 50, "offset": 0, "has_more": False}
    )
    result = invoke(["crm", "companies", "merge", "candidates"])
    assert result.exit_code == 0
    assert "No duplicate candidates" in result.output


# ---------------------------------------------------------------------------
# preview
# ---------------------------------------------------------------------------


def test_preview_sends_the_component_and_survivor(invoke, mock_api):
    route = mock_api.post(_PREVIEW).respond(200, json=PREVIEW_RESPONSE)
    result = invoke(
        [
            "crm",
            "companies",
            "merge",
            "preview",
            "--company-id",
            A,
            "--company-id",
            B,
            "--survivor",
            A,
        ]
    )
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert body == {"company_ids": [A, B], "survivor_id": A}


def test_preview_shows_the_reference_plan(invoke, mock_api):
    mock_api.post(_PREVIEW).respond(200, json=PREVIEW_RESPONSE)
    result = invoke(
        [
            "crm",
            "companies",
            "merge",
            "preview",
            "--company-id",
            A,
            "--company-id",
            B,
            "--survivor",
            A,
        ]
    )
    assert result.exit_code == 0
    assert "crm_activities" in result.output


def test_preview_json(invoke, mock_api):
    mock_api.post(_PREVIEW).respond(200, json=PREVIEW_RESPONSE)
    result = invoke(
        [
            "crm",
            "companies",
            "merge",
            "preview",
            "--json",
            "--company-id",
            A,
            "--company-id",
            B,
            "--survivor",
            A,
        ]
    )
    assert result.exit_code == 0
    assert json.loads(result.output)["survivor_id"] == A


# ---------------------------------------------------------------------------
# apply
# ---------------------------------------------------------------------------


def test_apply_requires_confirmation(invoke, mock_api):
    route = mock_api.post(_MERGE).respond(200, json=MERGE_RESPONSE)
    result = invoke(
        [
            "crm",
            "companies",
            "merge",
            "apply",
            "--company-id",
            A,
            "--company-id",
            B,
            "--survivor",
            A,
        ],
        input="n\n",
    )
    assert result.exit_code != 0
    assert not route.called


def test_apply_merges_with_yes(invoke, mock_api):
    route = mock_api.post(_MERGE).respond(200, json=MERGE_RESPONSE)
    result = invoke(
        [
            "crm",
            "companies",
            "merge",
            "apply",
            "--yes",
            "--company-id",
            A,
            "--company-id",
            B,
            "--survivor",
            A,
        ]
    )
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert body == {"company_ids": [A, B], "survivor_id": A}


def test_apply_omits_include_deleted_by_default(invoke, mock_api):
    """Absorbing a tombstone must never be a silent default."""
    route = mock_api.post(_MERGE).respond(200, json=MERGE_RESPONSE)
    result = invoke(
        [
            "crm",
            "companies",
            "merge",
            "apply",
            "--yes",
            "--company-id",
            A,
            "--company-id",
            B,
            "--survivor",
            A,
        ]
    )
    assert result.exit_code == 0
    assert "include_deleted" not in json.loads(route.calls.last.request.content)


def test_apply_forwards_include_deleted(invoke, mock_api):
    route = mock_api.post(_MERGE).respond(200, json=MERGE_RESPONSE)
    result = invoke(
        [
            "crm",
            "companies",
            "merge",
            "apply",
            "--yes",
            "--include-deleted",
            "--company-id",
            A,
            "--company-id",
            B,
            "--survivor",
            A,
        ]
    )
    assert result.exit_code == 0
    assert json.loads(route.calls.last.request.content)["include_deleted"] is True


def test_apply_forwards_field_selections(invoke, mock_api):
    route = mock_api.post(_MERGE).respond(200, json=MERGE_RESPONSE)
    result = invoke(
        [
            "crm",
            "companies",
            "merge",
            "apply",
            "--yes",
            "--company-id",
            A,
            "--company-id",
            B,
            "--survivor",
            A,
            "--set",
            f"website={B}",
        ]
    )
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert body["field_selections"] == {"website": B}


def test_apply_rejects_a_malformed_set(invoke, mock_api):
    route = mock_api.post(_MERGE).respond(200, json=MERGE_RESPONSE)
    result = invoke(
        [
            "crm",
            "companies",
            "merge",
            "apply",
            "--yes",
            "--company-id",
            A,
            "--company-id",
            B,
            "--survivor",
            A,
            "--set",
            "website",
        ]
    )
    assert result.exit_code == 2
    assert not route.called


def test_apply_reports_an_already_merged_loser(invoke, mock_api):
    """The idempotent re-run: nothing moved, and the CLI says so rather than
    claiming a merge happened."""
    mock_api.post(_MERGE).respond(
        200,
        json={
            "survivor_id": A,
            "merged": [],
            "already_merged": [B],
            "field_updates": {},
        },
    )
    result = invoke(
        [
            "crm",
            "companies",
            "merge",
            "apply",
            "--yes",
            "--company-id",
            A,
            "--company-id",
            B,
            "--survivor",
            A,
        ]
    )
    assert result.exit_code == 0
    assert "Merged 0" in result.output
    assert "already merged" in result.output.lower()


def test_apply_surfaces_a_conflict_error(invoke, mock_api):
    """409 is what the API returns for a tombstone loser without
    --include-deleted."""
    mock_api.post(_MERGE).respond(409, json={"detail": "Already deleted, cannot merge: " + B})
    result = invoke(
        [
            "crm",
            "companies",
            "merge",
            "apply",
            "--yes",
            "--company-id",
            A,
            "--company-id",
            B,
            "--survivor",
            A,
        ]
    )
    assert result.exit_code != 0
    assert "Already deleted" in result.output


def test_apply_json(invoke, mock_api):
    mock_api.post(_MERGE).respond(200, json=MERGE_RESPONSE)
    result = invoke(
        [
            "crm",
            "companies",
            "merge",
            "apply",
            "--yes",
            "--json",
            "--company-id",
            A,
            "--company-id",
            B,
            "--survivor",
            A,
        ]
    )
    assert result.exit_code == 0
    assert json.loads(result.output)["merged"] == [B]

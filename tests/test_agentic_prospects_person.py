"""A person prospect prints its person, and no company."""

import json

from ac_cli.commands.prospects import _SUMMARY_FIELDS
from tests.test_agentic_prospects import BASE, PROSPECT_ID, SUMMARY

_COLUMNS = [key for key, _ in _SUMMARY_FIELDS]
SUBJECT_COLUMN = _COLUMNS.index("subject_type")
PERSON_COLUMN = _COLUMNS.index("person_name")

PERSON_SUBJECT = {
    "id": "77777777-7777-4777-8777-777777777777",
    "linkedin_url": None,
    "full_name": "Jane Doe",
    "avatar_url": None,
    "current_title": "Marketing creator",
    "current_company_text": None,
    "location": "Bristol",
    "country": "United Kingdom",
    "email": None,
    "personal_website": "https://janedoe.example",
    "social_profile_url": "https://x.com/janedoe",
    "last_enriched_at": "2026-09-25T09:00:00Z",
}
PERSON_SUMMARY = {
    **SUMMARY,
    "subject_type": "person",
    "person": PERSON_SUBJECT,
    "company_name": None,
    "company_domain": None,
    "company_logo_url": None,
    "company_industry": None,
    "company_location": None,
}
PERSON_DETAIL = {**PERSON_SUMMARY, "company": None}
COMPANY_SUMMARY = {**SUMMARY, "subject_type": "company", "person": None}


def test_list_names_the_person_of_a_person_prospect(invoke, mock_api, table_column):
    mock_api.get(BASE).respond(
        200, json={"items": [PERSON_SUMMARY, COMPANY_SUMMARY], "next_cursor": None}
    )

    result = invoke(["agentic", "prospects", "list"])

    assert result.exit_code == 0
    # The helper joins the cells of one column, top row first, and a wrapped
    # cell loses its inner space.
    assert table_column(result.output, SUBJECT_COLUMN) == "personcompany"
    assert table_column(result.output, PERSON_COLUMN).replace(" ", "") == "JaneDoe"


def test_get_prints_the_person_and_no_company_block(invoke, mock_api):
    mock_api.get(f"{BASE}/{PROSPECT_ID}").respond(200, json=PERSON_DETAIL)

    result = invoke(["agentic", "prospects", "get", PROSPECT_ID])

    assert result.exit_code == 0
    # A block header is a line of its own. A detail row ends its label with a
    # colon, so "Company:" is a row and "Company" is the block.
    lines = [line.strip() for line in result.output.splitlines()]
    assert "Person" in lines
    assert "Company" not in lines
    assert "Jane Doe" in result.output
    assert "janedoe.example" in result.output
    assert "Marketing creator" in result.output


def test_get_json_keeps_the_null_company(invoke, mock_api):
    mock_api.get(f"{BASE}/{PROSPECT_ID}").respond(200, json=PERSON_DETAIL)

    result = invoke(["agentic", "prospects", "get", PROSPECT_ID, "--json"])

    assert json.loads(result.output)["company"] is None
    assert json.loads(result.output)["person"]["full_name"] == "Jane Doe"


EMPLOYER = {
    "id": "99999999-9999-4999-8999-999999999999",
    "name": "Copyhackers",
    "domain": "copyhackers.com",
    "logo_url": "https://cdn.example/copyhackers.png",
}
LINKED_SUBJECT = {
    **PERSON_SUBJECT,
    "current_company_text": "Copy Hackers Ltd",
    "current_company": EMPLOYER,
}


def _people_item(person: dict) -> dict:
    return {
        "id": "88888888-8888-4888-8888-888888888888",
        "prospect_id": PROSPECT_ID,
        "crm_person_id": None,
        "persona_fit_score": 91,
        "persona_fit_reason": None,
        "contact_state": "verified",
        "first_seen_at": "2026-09-25T09:00:00Z",
        "last_seen_at": "2026-09-25T09:00:00Z",
        "created_at": "2026-09-25T09:00:00Z",
        "updated_at": "2026-09-25T09:00:00Z",
        "person": person,
    }


def test_get_prints_the_linked_employer_of_the_person(invoke, mock_api):
    mock_api.get(f"{BASE}/{PROSPECT_ID}").respond(
        200, json={**PERSON_DETAIL, "person": LINKED_SUBJECT}
    )

    result = invoke(["agentic", "prospects", "get", PROSPECT_ID])

    assert result.exit_code == 0
    # The linked company names the employer. The free text is the fallback.
    assert "Copyhackers" in result.output
    assert "Copy Hackers Ltd" not in result.output


def test_get_falls_back_to_the_employer_text(invoke, mock_api):
    person = {**PERSON_SUBJECT, "current_company_text": "Copy Hackers Ltd"}
    mock_api.get(f"{BASE}/{PROSPECT_ID}").respond(200, json={**PERSON_DETAIL, "person": person})

    result = invoke(["agentic", "prospects", "get", PROSPECT_ID])

    assert result.exit_code == 0
    assert "Copy Hackers Ltd" in result.output


def test_people_prints_each_persons_linked_employer(invoke, mock_api):
    mock_api.get(f"{BASE}/{PROSPECT_ID}/people").respond(
        200,
        json={
            "items": [
                _people_item(LINKED_SUBJECT),
                _people_item(
                    {**PERSON_SUBJECT, "full_name": "Ann Text", "current_company_text": "Textual"}
                ),
            ],
            "next_cursor": None,
        },
    )

    result = invoke(["agentic", "prospects", "people", PROSPECT_ID])

    assert result.exit_code == 0
    assert "Copyhackers" in result.output
    assert "Copy Hackers Ltd" not in result.output
    assert "Textual" in result.output


def test_promote_prints_the_employer_crm_company_of_a_person_prospect(invoke, mock_api):
    mock_api.post(f"{BASE}/{PROSPECT_ID}/promote").respond(
        200,
        json={
            "prospect_id": PROSPECT_ID,
            "review_state": "promoted",
            "crm_company_id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
            "people": [
                {
                    "prospect_person_id": "88888888-8888-4888-8888-888888888888",
                    "intel_person_id": PERSON_SUBJECT["id"],
                    "crm_person_id": "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
                }
            ],
            "list_id": None,
        },
    )

    result = invoke(["agentic", "prospects", "promote", PROSPECT_ID, "--yes"])

    assert result.exit_code == 0
    assert "cccccccc-cccc-4ccc-8ccc-cccccccccccc" in result.output
    # The people table wraps a UUID cell, so the check names the table.
    assert "Promoted people" in result.output

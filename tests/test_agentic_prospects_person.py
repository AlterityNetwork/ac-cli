"""A person prospect prints its person, and no company."""

import json

from ac_cli.commands.prospects import _SUMMARY_FIELDS
from tests.test_agentic_prospects import BASE, DETAIL, PROSPECT_ID, SUMMARY

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


def _block_headers(output: str) -> list[str]:
    """The lines that hold only a block header, such as "Person"."""
    return [line.strip() for line in output.splitlines()]


def test_list_reads_a_row_with_no_subject_field_as_a_company(invoke, mock_api, table_column):
    # A row from before the subject field has no `subject_type` key and no
    # `person` key. The table names it as a company.
    assert "subject_type" not in SUMMARY
    mock_api.get(BASE).respond(200, json={"items": [SUMMARY], "next_cursor": None})

    result = invoke(["agentic", "prospects", "list"])

    assert result.exit_code == 0
    assert table_column(result.output, SUBJECT_COLUMN) == "company"
    assert table_column(result.output, PERSON_COLUMN) == ""


def test_list_json_keeps_the_person_rows_as_the_api_sent_them(invoke, mock_api):
    page = {"items": [PERSON_SUMMARY, COMPANY_SUMMARY], "next_cursor": None}
    mock_api.get(BASE).respond(200, json=page)

    result = invoke(["agentic", "prospects", "list", "--json"])

    # The JSON output does not carry the flat table keys.
    assert json.loads(result.output) == page


def test_get_prints_the_company_block_and_no_person_block_for_a_company(invoke, mock_api):
    mock_api.get(f"{BASE}/{PROSPECT_ID}").respond(
        200, json={**DETAIL, "subject_type": "company", "person": None}
    )

    result = invoke(["agentic", "prospects", "get", PROSPECT_ID])

    assert result.exit_code == 0
    lines = _block_headers(result.output)
    assert "Company" in lines
    assert "Person" not in lines
    assert "Software" in result.output


def test_act_on_a_person_prospect_prints_the_task_and_the_person(invoke, mock_api):
    task_id = "88888888-8888-4888-8888-888888888888"
    mock_api.post(f"{BASE}/{PROSPECT_ID}/act").respond(
        200,
        json={
            "prospect": PERSON_DETAIL,
            "result": {"kind": "create_task", "task_id": task_id},
        },
    )

    result = invoke(["agentic", "prospects", "act", PROSPECT_ID])

    assert result.exit_code == 0
    assert task_id in result.output
    lines = _block_headers(result.output)
    assert "Person" in lines
    assert "Company" not in lines
    assert "Jane Doe" in result.output


PERSON_PROMOTION = {
    "prospect_id": PROSPECT_ID,
    "review_state": "promoted",
    "crm_company_id": None,
    "people": [
        {
            "prospect_person_id": "99999999-9999-4999-8999-999999999999",
            "intel_person_id": PERSON_SUBJECT["id"],
            "crm_person_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        }
    ],
    "list_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
}


def test_promote_prints_a_person_prospect_with_no_crm_company(invoke, mock_api, table_column):
    route = mock_api.post(f"{BASE}/{PROSPECT_ID}/promote").respond(200, json=PERSON_PROMOTION)

    result = invoke(
        [
            "agentic",
            "prospects",
            "promote",
            PROSPECT_ID,
            "--list",
            PERSON_PROMOTION["list_id"],
            "--yes",
        ]
    )

    assert result.exit_code == 0
    assert json.loads(route.calls[0].request.content) == {
        "person_ids": [],
        "list_id": PERSON_PROMOTION["list_id"],
    }
    assert "promoted" in result.output
    # A null CRM company prints as an empty value, not as "None".
    assert "CRM company ID: \n" in result.output
    assert "CRM list ID: bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb" in result.output
    # The third column of the people table holds the CRM person ID.
    assert table_column(result.output, 2) == "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


def test_promote_json_keeps_the_null_crm_company(invoke, mock_api):
    mock_api.post(f"{BASE}/{PROSPECT_ID}/promote").respond(200, json=PERSON_PROMOTION)

    result = invoke(["agentic", "prospects", "promote", PROSPECT_ID, "--yes", "--json"])

    assert json.loads(result.output) == PERSON_PROMOTION

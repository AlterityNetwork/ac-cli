"""Tests for the Envoy campaign, enrollment and organization stop commands."""

import json

import httpx
import pytest

BASE = "/api/v1/agentic/envoy"
CAMPAIGN_ID = "33333333-3333-4333-8333-333333333333"
ENROLLMENT_ID = "22222222-2222-4222-8222-222222222222"
PERSON_ID = "77777777-7777-4777-8777-777777777777"

CAMPAIGN = {
    "id": CAMPAIGN_ID,
    "name": "Q4 intro",
    "status": "draft",
    "description": "Heads of growth at Series A SaaS companies",
    "goal": "Book a 20 min intro call",
    "allowed_channels": ["email", "linkedin"],
    "max_touches": 5,
    "followup_min_days": 3,
    "followup_max_days": 7,
    "sender_user_id": "99999999-9999-4999-8999-999999999999",
    "created_by": "99999999-9999-4999-8999-999999999999",
    "created_at": "2026-10-21T10:00:00Z",
    "updated_at": "2026-10-21T10:00:00Z",
}
ENROLLMENT = {
    "id": ENROLLMENT_ID,
    "campaign_id": CAMPAIGN_ID,
    "person_kind": "crm.person",
    "person_id": PERSON_ID,
    "status": "active",
    "ended_reason": None,
    "next_check_at": "2026-10-21T10:30:00Z",
    "context_version": 1,
    "touch_count": 0,
    "enrolled_at": "2026-10-21T10:00:00Z",
    "ended_at": None,
    "updated_at": "2026-10-21T10:00:00Z",
}
BATCH_RESULTS = [
    {
        "person_kind": "crm.person",
        "person_id": PERSON_ID,
        "outcome": "added",
        "enrollment_id": ENROLLMENT_ID,
        "campaign_id": None,
        "campaign_name": None,
        "campaign_status": None,
    },
    {
        "person_kind": "prospect.person",
        "person_id": "88888888-8888-4888-8888-888888888888",
        "outcome": "already_enrolled",
        "enrollment_id": "55555555-5555-4555-8555-555555555555",
        "campaign_id": "44444444-4444-4444-8444-444444444444",
        "campaign_name": "Q1 nurture",
        "campaign_status": "paused",
    },
    {
        "person_kind": "crm.person",
        "person_id": "99999999-9999-4999-8999-999999999990",
        "outcome": "opted_out",
        "enrollment_id": None,
        "campaign_id": None,
        "campaign_name": None,
        "campaign_status": None,
    },
    {
        "person_kind": "crm.person",
        "person_id": "99999999-9999-4999-8999-999999999991",
        "outcome": "not_found",
        "enrollment_id": None,
        "campaign_id": None,
        "campaign_name": None,
        "campaign_status": None,
    },
    {
        "person_kind": "crm.person",
        "person_id": "99999999-9999-4999-8999-999999999992",
        "outcome": "campaign_full",
        "enrollment_id": None,
        "campaign_id": None,
        "campaign_name": None,
        "campaign_status": None,
    },
]
STOP = {"stopped": True, "stopped_at": "2026-10-21T10:00:00Z"}
COUNTS = {
    "active": 125,
    "needs_contact_data": 12,
    "ended": 41,
    "live": 140,
    "cap": 200,
}
ROW = {
    **ENROLLMENT,
    "person_name": "Jane Doe",
    "email": "jane@acme.test",
    "last_decision": {
        "id": "66666666-6666-4666-8666-666666666666",
        "type": "email",
        "status": "saved",
        "created_at": "2026-10-21T11:00:00Z",
    },
    "awaiting_approval": True,
}
PAGE = {"data": [ROW], "total": 3, "limit": 1, "offset": 1, "has_more": True}


def _added(request) -> httpx.Response:
    """Answers each person of a batch request as added, in order."""
    people = json.loads(request.content)["people"]
    return httpx.Response(
        200,
        json={
            "results": [
                {
                    **one,
                    "outcome": "added",
                    "enrollment_id": ENROLLMENT_ID,
                    "campaign_id": None,
                    "campaign_name": None,
                    "campaign_status": None,
                }
                for one in people
            ]
        },
    )


def _body(route) -> dict:
    return json.loads(route.calls[0].request.content)


class TestCampaigns:
    def test_list_sends_the_filters(self, invoke, mock_api):
        route = mock_api.get(f"{BASE}/campaigns").respond(200, json={"items": [CAMPAIGN]})

        result = invoke(
            ["agentic", "envoy", "campaigns", "list", "--status", "draft", "--limit", "5"]
        )

        assert result.exit_code == 0, result.output
        params = route.calls[0].request.url.params
        assert (params["status"], params["limit"]) == ("draft", "5")
        assert "Q4 intro" in result.output

    def test_list_sends_the_offset_and_names_the_page(self, invoke, mock_api):
        page = {"items": [CAMPAIGN], "total": 3, "limit": 1, "offset": 1, "has_more": True}
        route = mock_api.get(f"{BASE}/campaigns").respond(200, json=page)

        result = invoke(["agentic", "envoy", "campaigns", "list", "--limit", "1", "--offset", "1"])

        assert result.exit_code == 0, result.output
        assert route.calls[0].request.url.params["offset"] == "1"
        assert "2-2 of 3" in result.output
        assert "--offset 2" in result.output

    def test_a_list_past_the_end_names_the_total_and_no_next_offset(self, invoke, mock_api):
        page = {"items": [], "total": 3, "limit": 50, "offset": 10, "has_more": False}
        mock_api.get(f"{BASE}/campaigns").respond(200, json=page)

        result = invoke(["agentic", "envoy", "campaigns", "list", "--offset", "10"])

        assert result.exit_code == 0, result.output
        assert "0 of 3" in result.output
        assert "--offset" not in result.output

    def test_list_refuses_a_negative_offset_without_a_call(self, invoke, mock_api):
        route = mock_api.get(f"{BASE}/campaigns").respond(200, json={"items": []})

        result = invoke(["agentic", "envoy", "campaigns", "list", "--offset", "-1"])

        assert result.exit_code == 2
        assert not route.called

    def test_list_and_get_print_the_enrollment_counts(self, invoke, mock_api):
        counted = {**CAMPAIGN, "enrollment_counts": COUNTS}
        mock_api.get(f"{BASE}/campaigns").respond(200, json={"items": [counted]})
        mock_api.get(f"{BASE}/campaigns/{CAMPAIGN_ID}").respond(200, json=counted)

        listed = invoke(["agentic", "envoy", "campaigns", "list"])
        read = invoke(["agentic", "envoy", "campaigns", "get", CAMPAIGN_ID])

        assert listed.exit_code == 0, listed.output
        assert read.exit_code == 0, read.output
        for output in (listed.output, read.output):
            for text in ("140/200", "12", "41"):
                assert text in output
        assert "Needs email" in read.output
        for output in (listed.output, read.output):
            assert "Awaiting" not in output

    def test_create_prints_no_count_lines(self, invoke, mock_api):
        mock_api.post(f"{BASE}/campaigns").respond(201, json=CAMPAIGN)

        result = invoke(
            ["agentic", "envoy", "campaigns", "create", "--name", "Q4 intro", "--goal", "G"]
        )

        assert result.exit_code == 0, result.output
        assert "Needs email" not in result.output
        assert "People" not in result.output

    def test_a_campaign_without_counts_prints_no_none(self, invoke, mock_api):
        mock_api.get(f"{BASE}/campaigns").respond(200, json={"items": [CAMPAIGN]})

        result = invoke(["agentic", "envoy", "campaigns", "list"])

        assert result.exit_code == 0, result.output
        assert "None" not in result.output

    def test_list_refuses_a_bad_status_without_a_call(self, invoke, mock_api):
        route = mock_api.get(f"{BASE}/campaigns").respond(200, json={"items": []})

        result = invoke(["agentic", "envoy", "campaigns", "list", "--status", "live"])

        assert result.exit_code == 2
        assert not route.called

    def test_get_prints_the_campaign(self, invoke, mock_api):
        mock_api.get(f"{BASE}/campaigns/{CAMPAIGN_ID}").respond(200, json=CAMPAIGN)

        result = invoke(["agentic", "envoy", "campaigns", "get", CAMPAIGN_ID, "--json"])

        assert json.loads(result.output) == CAMPAIGN

    def test_create_sends_only_the_given_fields(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/campaigns").respond(201, json=CAMPAIGN)

        result = invoke(
            [
                "agentic",
                "envoy",
                "campaigns",
                "create",
                "--name",
                "Q4 intro",
                "--goal",
                "Book a call",
                "--description",
                "Heads of growth",
            ]
        )

        assert result.exit_code == 0, result.output
        assert _body(route) == {
            "name": "Q4 intro",
            "goal": "Book a call",
            "description": "Heads of growth",
        }
        assert "Heads of growth at Series A SaaS companies" in result.output

    def test_create_without_a_description_sends_only_the_name_and_goal(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/campaigns").respond(201, json=CAMPAIGN)

        result = invoke(
            ["agentic", "envoy", "campaigns", "create", "--name", "Q4 intro", "--goal", "G"]
        )

        assert result.exit_code == 0, result.output
        assert _body(route) == {"name": "Q4 intro", "goal": "G"}

    def test_update_clears_the_description_with_an_empty_value(self, invoke, mock_api):
        route = mock_api.patch(f"{BASE}/campaigns/{CAMPAIGN_ID}").respond(200, json=CAMPAIGN)

        result = invoke(
            [
                "agentic",
                "envoy",
                "campaigns",
                "update",
                CAMPAIGN_ID,
                "--description",
                "",
            ]
        )

        assert result.exit_code == 0, result.output
        assert _body(route) == {"description": ""}

    def test_update_with_nothing_refuses_without_a_call(self, invoke, mock_api):
        route = mock_api.patch(f"{BASE}/campaigns/{CAMPAIGN_ID}").respond(200, json=CAMPAIGN)

        result = invoke(["agentic", "envoy", "campaigns", "update", CAMPAIGN_ID])

        assert result.exit_code == 2
        assert not route.called

    def test_a_too_long_description_is_refused_without_a_call(self, invoke, mock_api):
        created = mock_api.post(f"{BASE}/campaigns").respond(201, json=CAMPAIGN)
        updated = mock_api.patch(f"{BASE}/campaigns/{CAMPAIGN_ID}").respond(200, json=CAMPAIGN)
        too_long = "x" * 2001

        for args in (
            ["create", "--name", "Q3", "--goal", "G", "--description", too_long],
            ["update", CAMPAIGN_ID, "--description", too_long],
        ):
            result = invoke(["agentic", "envoy", "campaigns", *args])
            assert result.exit_code == 2, args
        assert not created.called
        assert not updated.called

    def test_a_description_of_the_maximum_length_is_sent(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/campaigns").respond(201, json=CAMPAIGN)

        result = invoke(
            [
                "agentic",
                "envoy",
                "campaigns",
                "create",
                "--name",
                "Q3",
                "--goal",
                "G",
                "--description",
                "x" * 2000,
            ]
        )

        assert result.exit_code == 0, result.output
        assert route.called

    def test_each_status_command_posts_its_status(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/campaigns/{CAMPAIGN_ID}/status").respond(200, json=CAMPAIGN)

        for command, status in (
            ("activate", "active"),
            ("pause", "paused"),
            ("resume", "active"),
            ("archive", "archived"),
        ):
            args = ["agentic", "envoy", "campaigns", command, CAMPAIGN_ID]
            result = invoke([*args, "--yes"] if command == "archive" else args)
            assert result.exit_code == 0, result.output
            assert json.loads(route.calls[-1].request.content) == {"status": status}

    def test_each_status_command_prints_json(self, invoke, mock_api):
        mock_api.post(f"{BASE}/campaigns/{CAMPAIGN_ID}/status").respond(200, json=CAMPAIGN)

        for command in ("activate", "pause", "resume", "archive"):
            args = ["agentic", "envoy", "campaigns", command, CAMPAIGN_ID, "--json"]
            result = invoke([*args, "--yes"] if command == "archive" else args)
            assert json.loads(result.output) == CAMPAIGN

    def test_list_and_create_print_json(self, invoke, mock_api):
        mock_api.get(f"{BASE}/campaigns").respond(200, json={"items": [CAMPAIGN]})
        mock_api.post(f"{BASE}/campaigns").respond(201, json=CAMPAIGN)

        listed = invoke(["agentic", "envoy", "campaigns", "list", "--json"])
        created = invoke(
            ["agentic", "envoy", "campaigns", "create", "--name", "X", "--goal", "G", "--json"]
        )

        assert json.loads(listed.output) == {"items": [CAMPAIGN]}
        assert json.loads(created.output) == CAMPAIGN

    def test_the_removed_campaign_options_are_refused_without_a_call(self, invoke, mock_api):
        create = mock_api.post(f"{BASE}/campaigns").respond(201, json=CAMPAIGN)
        update = mock_api.patch(f"{BASE}/campaigns/{CAMPAIGN_ID}").respond(200, json=CAMPAIGN)

        for option, value in (
            ("--instructions", "Be brief"),
            ("--max-emails", "3"),
            ("--writing-style-id", "none"),
            ("--playbook-id", "none"),
            ("--battlecard-id", "none"),
        ):
            for args in (
                ["create", "--name", "X", "--goal", "G", option, value],
                ["update", CAMPAIGN_ID, option, value],
            ):
                result = invoke(["agentic", "envoy", "campaigns", *args])
                assert result.exit_code == 2, args
        assert not create.called
        assert not update.called

    def test_get_prints_the_description_and_no_removed_field(self, invoke, mock_api):
        mock_api.get(f"{BASE}/campaigns/{CAMPAIGN_ID}").respond(200, json=CAMPAIGN)

        result = invoke(["agentic", "envoy", "campaigns", "get", CAMPAIGN_ID])

        assert result.exit_code == 0, result.output
        assert "Description" in result.output
        assert "Heads of growth at Series A SaaS companies" in result.output
        for label in ("Instructions", "Max emails", "Writing style", "Playbook"):
            assert label not in result.output

    def test_get_prints_the_goal_channels_limits_and_sender(self, invoke, mock_api):
        mock_api.get(f"{BASE}/campaigns/{CAMPAIGN_ID}").respond(200, json=CAMPAIGN)

        result = invoke(["agentic", "envoy", "campaigns", "get", CAMPAIGN_ID])

        assert result.exit_code == 0, result.output
        for text in (
            "Goal",
            "Book a 20 min intro call",
            "Channels",
            "email, linkedin",
            "Max touches",
            "Follow-up",
            "3 to 7 days",
            "Sender",
            "99999999-9999-4999-8999-999999999999",
        ):
            assert text in result.output

    def test_list_prints_the_channels(self, invoke, mock_api, table_column):
        mock_api.get(f"{BASE}/campaigns").respond(200, json={"items": [CAMPAIGN]})

        result = invoke(["agentic", "envoy", "campaigns", "list"])

        assert result.exit_code == 0, result.output
        # A narrow terminal folds the cell at the space, and the reader drops it.
        assert table_column(result.output, 3).replace(" ", "") == "email,linkedin"

    def test_create_sends_the_context_options(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/campaigns").respond(201, json=CAMPAIGN)

        result = invoke(
            [
                "agentic",
                "envoy",
                "campaigns",
                "create",
                "--name",
                "Q4",
                "--goal",
                "Book a call",
                "--channel",
                "linkedin",
                "--channel",
                "email",
                "--max-touches",
                "4",
                "--min-days",
                "2",
                "--max-days",
                "9",
            ]
        )

        assert result.exit_code == 0, result.output
        assert _body(route) == {
            "name": "Q4",
            "goal": "Book a call",
            "allowed_channels": ["linkedin", "email"],
            "max_touches": 4,
            "followup_min_days": 2,
            "followup_max_days": 9,
        }

    def test_update_sends_only_the_given_context_options(self, invoke, mock_api):
        route = mock_api.patch(f"{BASE}/campaigns/{CAMPAIGN_ID}").respond(200, json=CAMPAIGN)

        result = invoke(
            [
                "agentic",
                "envoy",
                "campaigns",
                "update",
                CAMPAIGN_ID,
                "--goal",
                "Book a demo",
                "--channel",
                "email",
                "--max-days",
                "10",
            ]
        )

        assert result.exit_code == 0, result.output
        assert _body(route) == {
            "goal": "Book a demo",
            "allowed_channels": ["email"],
            "followup_max_days": 10,
        }

    def test_create_requires_a_goal(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/campaigns").respond(201, json=CAMPAIGN)

        result = invoke(["agentic", "envoy", "campaigns", "create", "--name", "Q4"])
        as_json = invoke(["agentic", "envoy", "campaigns", "create", "--name", "Q4", "--json"])

        assert result.exit_code == 2
        assert as_json.exit_code == 2
        assert json.loads(as_json.output)["error"] is True
        assert not route.called

    @pytest.mark.parametrize(
        "args",
        [
            ["--goal", " "],
            ["--goal", "x" * 2001],
            ["--channel", "sms"],
            ["--max-touches", "0"],
            ["--max-touches", "11"],
            ["--min-days", "0"],
            ["--max-days", "31"],
            ["--min-days", "8", "--max-days", "7"],
        ],
    )
    def test_a_bad_context_option_is_refused_without_a_call(self, invoke, mock_api, args):
        created = mock_api.post(f"{BASE}/campaigns").respond(201, json=CAMPAIGN)
        updated = mock_api.patch(f"{BASE}/campaigns/{CAMPAIGN_ID}").respond(200, json=CAMPAIGN)
        goal = [] if args[0] == "--goal" else ["--goal", "G"]

        for command in (
            ["create", "--name", "Q4", *goal, *args],
            ["update", CAMPAIGN_ID, *args],
        ):
            result = invoke(["agentic", "envoy", "campaigns", *command])
            assert result.exit_code == 2, (command, result.output)
        assert not created.called
        assert not updated.called

    def test_there_is_no_sender_option(self, invoke, mock_api):
        """The sender is always the creator, so no option names it."""
        created = mock_api.post(f"{BASE}/campaigns").respond(201, json=CAMPAIGN)
        updated = mock_api.patch(f"{BASE}/campaigns/{CAMPAIGN_ID}").respond(200, json=CAMPAIGN)
        sender = "11111111-1111-4111-8111-111111111111"

        for command in (
            ["create", "--name", "Q4", "--goal", "G", "--sender", sender],
            ["update", CAMPAIGN_ID, "--sender", sender],
        ):
            result = invoke(["agentic", "envoy", "campaigns", *command])
            assert result.exit_code == 2, command
        assert not created.called
        assert not updated.called

    def test_archive_asks_first(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/campaigns/{CAMPAIGN_ID}/status").respond(200, json=CAMPAIGN)

        result = invoke(["agentic", "envoy", "campaigns", "archive", CAMPAIGN_ID], input="n\n")

        assert result.exit_code == 1
        assert not route.called

    def test_enroll_posts_the_person(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/campaigns/{CAMPAIGN_ID}/enrollments").respond(
            201, json=ENROLLMENT
        )

        result = invoke(
            [
                "agentic",
                "envoy",
                "campaigns",
                "enroll",
                CAMPAIGN_ID,
                "--person-kind",
                "crm.person",
                "--person-id",
                PERSON_ID,
            ]
        )

        assert result.exit_code == 0, result.output
        assert _body(route) == {"person_kind": "crm.person", "person_id": PERSON_ID}

    def test_enroll_shows_the_first_campaign_on_409(self, invoke, mock_api):
        mock_api.post(f"{BASE}/campaigns/{CAMPAIGN_ID}/enrollments").respond(
            409,
            json={
                "error": "Conflict",
                "message": 'The person is already enrolled in the campaign "Q1".',
                "type": "conflict",
                "context": {"code": "already_enrolled", "campaign_name": "Q1"},
                "code": "already_enrolled",
            },
        )

        result = invoke(
            [
                "agentic",
                "envoy",
                "campaigns",
                "enroll",
                CAMPAIGN_ID,
                "--person-kind",
                "crm.person",
                "--person-id",
                PERSON_ID,
            ]
        )

        assert result.exit_code == 5
        assert "Q1" in result.output

    @pytest.mark.parametrize("json_flag", [[], ["--json"]])
    def test_enroll_shows_the_opted_out_refusal(self, invoke, mock_api, json_flag):
        message = "The email address of the person is on the do-not-contact list."
        mock_api.post(f"{BASE}/campaigns/{CAMPAIGN_ID}/enrollments").respond(
            409,
            json={
                "error": "Conflict",
                "message": message,
                "type": "conflict",
                "context": {"code": "opted_out"},
                "code": "opted_out",
            },
        )

        result = invoke(
            [
                "agentic",
                "envoy",
                "campaigns",
                "enroll",
                CAMPAIGN_ID,
                "--person-kind",
                "crm.person",
                "--person-id",
                PERSON_ID,
                *json_flag,
            ]
        )

        assert result.exit_code == 5
        assert "do-not-contact list" in result.output
        if json_flag:
            assert "opted_out" in result.output

    def test_enroll_batch_posts_the_flags_then_the_file_in_order(self, invoke, mock_api, tmp_path):
        other = "88888888-8888-4888-8888-888888888888"
        third = "99999999-9999-4999-8999-999999999990"
        path = tmp_path / "people.txt"
        path.write_text(f"# Signals list\n\nprospect.person:{other}\n  crm.person:{third}  \n")
        route = mock_api.post(f"{BASE}/campaigns/{CAMPAIGN_ID}/enrollments/batch").respond(
            200, json={"results": BATCH_RESULTS}
        )

        result = invoke(
            [
                "agentic",
                "envoy",
                "campaigns",
                "enroll-batch",
                CAMPAIGN_ID,
                "--person",
                f"crm.person:{PERSON_ID}",
                "--file",
                str(path),
            ]
        )

        assert result.exit_code == 0, result.output
        assert _body(route) == {
            "people": [
                {"person_kind": "crm.person", "person_id": PERSON_ID},
                {"person_kind": "prospect.person", "person_id": other},
                {"person_kind": "crm.person", "person_id": third},
            ]
        }
        for text in (
            "added",
            "already_enrolled",
            'In "Q1 nurture" (paused)',
            "opted_out",
            "do-not-contact",
            "not_found",
            "campaign_full",
            "1 of 5 added",
        ):
            assert text in result.output

    def test_enroll_batch_prints_the_json_answer(self, invoke, mock_api):
        mock_api.post(f"{BASE}/campaigns/{CAMPAIGN_ID}/enrollments/batch").respond(
            200, json={"results": BATCH_RESULTS[:1]}
        )

        result = invoke(
            [
                "agentic",
                "envoy",
                "campaigns",
                "enroll-batch",
                CAMPAIGN_ID,
                "--person",
                f"crm.person:{PERSON_ID}",
                "--json",
            ]
        )

        assert result.exit_code == 0, result.output
        assert json.loads(result.output) == {"results": BATCH_RESULTS[:1]}

    @pytest.mark.parametrize(
        "person",
        ["crm.person", f"lead:{PERSON_ID}", "crm.person:not-a-uuid", f":{PERSON_ID}"],
    )
    def test_enroll_batch_refuses_a_bad_person_without_a_call(self, invoke, mock_api, person):
        route = mock_api.post(f"{BASE}/campaigns/{CAMPAIGN_ID}/enrollments/batch")

        result = invoke(
            [
                "agentic",
                "envoy",
                "campaigns",
                "enroll-batch",
                CAMPAIGN_ID,
                "--person",
                person,
                "--json",
            ]
        )

        assert result.exit_code == 2
        assert json.loads(result.output)["error"] is True
        assert not route.called

    def test_enroll_batch_refuses_no_people_and_more_than_200(self, invoke, mock_api, tmp_path):
        route = mock_api.post(f"{BASE}/campaigns/{CAMPAIGN_ID}/enrollments/batch")
        path = tmp_path / "many.txt"
        path.write_text("".join(f"crm.person:{PERSON_ID[:-3]}{n:03d}\n" for n in range(201)))

        empty = invoke(["agentic", "envoy", "campaigns", "enroll-batch", CAMPAIGN_ID])
        many = invoke(
            ["agentic", "envoy", "campaigns", "enroll-batch", CAMPAIGN_ID, "--file", str(path)]
        )

        assert (empty.exit_code, many.exit_code) == (2, 2)
        assert "200" in many.output
        assert not route.called

    def test_enroll_batch_reads_a_bom_file_and_sends_each_person_once(
        self, invoke, mock_api, tmp_path
    ):
        path = tmp_path / "people.txt"
        path.write_text(
            f"crm.person:{PERSON_ID.upper()}\r\ncrm.person:{PERSON_ID}\r\n",
            encoding="utf-8-sig",
        )
        route = mock_api.post(f"{BASE}/campaigns/{CAMPAIGN_ID}/enrollments/batch").respond(
            200, json={"results": BATCH_RESULTS[:1]}
        )

        result = invoke(
            [
                "agentic",
                "envoy",
                "campaigns",
                "enroll-batch",
                CAMPAIGN_ID,
                "--person",
                f"crm.person:{PERSON_ID}",
                "--file",
                str(path),
            ]
        )

        assert result.exit_code == 0, result.output
        assert _body(route) == {"people": [{"person_kind": "crm.person", "person_id": PERSON_ID}]}

    def test_enroll_batch_accepts_exactly_200_people(self, invoke, mock_api, tmp_path):
        path = tmp_path / "many.txt"
        path.write_text("".join(f"crm.person:{PERSON_ID[:-3]}{n:03d}\n" for n in range(200)))
        route = mock_api.post(f"{BASE}/campaigns/{CAMPAIGN_ID}/enrollments/batch").mock(
            side_effect=_added
        )

        result = invoke(
            ["agentic", "envoy", "campaigns", "enroll-batch", CAMPAIGN_ID, "--file", str(path)]
        )

        assert result.exit_code == 0, result.output
        assert [len(json.loads(c.request.content)["people"]) for c in route.calls] == [50] * 4
        assert "200 of 200 added" in result.output

    def test_enroll_batch_refuses_a_file_that_is_not_utf8(self, invoke, mock_api, tmp_path):
        path = tmp_path / "people.txt"
        path.write_bytes(f"crm.person:{PERSON_ID}\n".encode("utf-16"))
        route = mock_api.post(f"{BASE}/campaigns/{CAMPAIGN_ID}/enrollments/batch")

        result = invoke(
            [
                "agentic",
                "envoy",
                "campaigns",
                "enroll-batch",
                CAMPAIGN_ID,
                "--file",
                str(path),
                "--json",
            ]
        )

        assert result.exit_code == 2
        assert json.loads(result.output)["error"] is True
        assert not route.called

    def test_enroll_batch_names_a_campaign_with_no_status(self, invoke, mock_api):
        row = {**BATCH_RESULTS[1], "campaign_status": None}
        mock_api.post(f"{BASE}/campaigns/{CAMPAIGN_ID}/enrollments/batch").respond(
            200, json={"results": [row]}
        )

        result = invoke(
            [
                "agentic",
                "envoy",
                "campaigns",
                "enroll-batch",
                CAMPAIGN_ID,
                "--person",
                f"prospect.person:{row['person_id']}",
            ]
        )

        assert result.exit_code == 0, result.output
        assert "None" not in result.output
        assert 'In "Q1 nurture"' in result.output

    def test_enroll_batch_sends_120_people_in_chunks_of_50_in_order(
        self, invoke, mock_api, tmp_path
    ):
        ids = [f"{PERSON_ID[:-3]}{n:03d}" for n in range(120)]
        path = tmp_path / "many.txt"
        path.write_text("".join(f"crm.person:{one}\n" for one in ids))
        route = mock_api.post(f"{BASE}/campaigns/{CAMPAIGN_ID}/enrollments/batch").mock(
            side_effect=lambda request: _added(request)
        )

        result = invoke(
            [
                "agentic",
                "envoy",
                "campaigns",
                "enroll-batch",
                CAMPAIGN_ID,
                "--file",
                str(path),
                "--json",
            ]
        )

        assert result.exit_code == 0, result.output
        sizes = [len(json.loads(call.request.content)["people"]) for call in route.calls]
        assert sizes == [50, 50, 20]
        results = json.loads(result.output)["results"]
        assert [one["person_id"] for one in results] == ids

    def test_enroll_batch_reports_the_sent_chunks_when_a_later_one_fails(
        self, invoke, mock_api, tmp_path
    ):
        ids = [f"{PERSON_ID[:-3]}{n:03d}" for n in range(60)]
        path = tmp_path / "many.txt"
        path.write_text("".join(f"crm.person:{one}\n" for one in ids))
        answers = iter(
            [
                None,
                httpx.Response(
                    409,
                    json={
                        "error": "Conflict",
                        "message": "The campaign is archived.",
                        "type": "conflict",
                        "context": {"code": "campaign_archived"},
                        "code": "campaign_archived",
                    },
                ),
            ]
        )

        def answer(request):
            planned = next(answers)
            return planned if planned is not None else _added(request)

        route = mock_api.post(f"{BASE}/campaigns/{CAMPAIGN_ID}/enrollments/batch").mock(
            side_effect=answer
        )

        result = invoke(
            ["agentic", "envoy", "campaigns", "enroll-batch", CAMPAIGN_ID, "--file", str(path)]
        )

        assert result.exit_code == 5
        assert route.call_count == 2
        assert "archived" in result.output
        assert "50 of 60 added" in result.output
        assert "not_sent" in result.output

    def test_enroll_batch_refuses_a_missing_file(self, invoke, mock_api, tmp_path):
        result = invoke(
            [
                "agentic",
                "envoy",
                "campaigns",
                "enroll-batch",
                CAMPAIGN_ID,
                "--file",
                str(tmp_path / "missing.txt"),
            ]
        )

        assert result.exit_code == 2
        assert not mock_api.calls

    def test_enroll_batch_shows_a_campaign_refusal(self, invoke, mock_api):
        mock_api.post(f"{BASE}/campaigns/{CAMPAIGN_ID}/enrollments/batch").respond(
            409,
            json={
                "error": "Conflict",
                "message": "The campaign is archived.",
                "type": "conflict",
                "context": {"code": "campaign_archived"},
                "code": "campaign_archived",
            },
        )

        result = invoke(
            [
                "agentic",
                "envoy",
                "campaigns",
                "enroll-batch",
                CAMPAIGN_ID,
                "--person",
                f"crm.person:{PERSON_ID}",
            ]
        )

        assert result.exit_code == 5
        assert "archived" in result.output

    def test_enroll_refuses_a_bad_person_kind_without_a_call(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/campaigns/{CAMPAIGN_ID}/enrollments").respond(
            201, json=ENROLLMENT
        )

        result = invoke(
            [
                "agentic",
                "envoy",
                "campaigns",
                "enroll",
                CAMPAIGN_ID,
                "--person-kind",
                "lead",
                "--person-id",
                PERSON_ID,
            ]
        )

        assert result.exit_code == 2
        assert not route.called


class TestEnrollments:
    def test_list_reads_one_campaign(self, invoke, mock_api, table_column):
        route = mock_api.get(f"{BASE}/campaigns/{CAMPAIGN_ID}/enrollments").respond(200, json=PAGE)

        result = invoke(
            [
                "agentic",
                "envoy",
                "enrollments",
                "list",
                "--campaign-id",
                CAMPAIGN_ID,
                "--status",
                "active",
                "--search",
                "jane",
                "--limit",
                "1",
                "--offset",
                "1",
            ]
        )

        assert result.exit_code == 0, result.output
        params = route.calls[0].request.url.params
        assert (params["status"], params["search"], params["limit"], params["offset"]) == (
            "active",
            "jane",
            "1",
            "1",
        )
        assert "Envoy enrollments 2-2 of 3" in result.output
        assert table_column(result.output, 1) == "Jane Doe"
        assert table_column(result.output, 2) == "jane@acme.test"
        # The fold drops the space at the end of a line part.
        assert table_column(result.output, 4).replace(" ", "") == "email·saved"
        assert "--offset 2" in result.output

    def test_list_without_a_search_sends_no_search(self, invoke, mock_api):
        route = mock_api.get(f"{BASE}/campaigns/{CAMPAIGN_ID}/enrollments").respond(
            200, json={"data": [], "total": 0, "limit": 100, "offset": 0, "has_more": False}
        )

        result = invoke(["agentic", "envoy", "enrollments", "list", "--campaign-id", CAMPAIGN_ID])

        assert result.exit_code == 0, result.output
        params = route.calls[0].request.url.params
        assert "search" not in params
        assert params["offset"] == "0"
        assert "0 of 0" in result.output
        assert "--offset" not in result.output

    def test_list_refuses_a_bad_offset_or_search_without_a_call(self, invoke, mock_api):
        route = mock_api.get(f"{BASE}/campaigns/{CAMPAIGN_ID}/enrollments")
        base = ["agentic", "envoy", "enrollments", "list", "--campaign-id", CAMPAIGN_ID]

        negative = invoke([*base, "--offset", "-1"])
        long = invoke([*base, "--search", "x" * 101])

        assert (negative.exit_code, long.exit_code) == (2, 2)
        assert not route.called

    def test_list_json_keeps_the_page(self, invoke, mock_api):
        mock_api.get(f"{BASE}/campaigns/{CAMPAIGN_ID}/enrollments").respond(200, json=PAGE)

        result = invoke(
            ["agentic", "envoy", "enrollments", "list", "--campaign-id", CAMPAIGN_ID, "--json"]
        )

        assert json.loads(result.output) == PAGE

    def test_list_refuses_a_bad_limit_without_a_call(self, invoke, mock_api):
        route = mock_api.get(f"{BASE}/campaigns/{CAMPAIGN_ID}/enrollments").respond(
            200, json={"data": [], "total": 0, "limit": 1, "offset": 0, "has_more": False}
        )

        result = invoke(
            [
                "agentic",
                "envoy",
                "enrollments",
                "list",
                "--campaign-id",
                CAMPAIGN_ID,
                "--limit",
                "201",
            ]
        )

        assert result.exit_code == 2
        assert not route.called

    def test_get_prints_the_enrollment(self, invoke, mock_api):
        mock_api.get(f"{BASE}/enrollments/{ENROLLMENT_ID}").respond(200, json=ENROLLMENT)

        result = invoke(["agentic", "envoy", "enrollments", "get", ENROLLMENT_ID])

        assert result.exit_code == 0, result.output
        assert "crm.person" in result.output
        for label in ("Status", "Next check", "Context version", "Touches"):
            assert label in result.output
        assert "2026-10-21T10:30:00Z" in result.output
        assert "Run holding it" not in result.output

    def test_list_refuses_awaiting_approval_without_a_call(self, invoke, mock_api):
        route = mock_api.get(f"{BASE}/campaigns/{CAMPAIGN_ID}/enrollments").respond(200, json=PAGE)

        result = invoke(
            [
                "agentic",
                "envoy",
                "enrollments",
                "list",
                "--campaign-id",
                CAMPAIGN_ID,
                "--status",
                "awaiting_approval",
                "--json",
            ]
        )

        assert result.exit_code == 2
        assert not route.called

    def test_list_has_no_state_option(self, invoke, mock_api):
        route = mock_api.get(f"{BASE}/campaigns/{CAMPAIGN_ID}/enrollments").respond(200, json=PAGE)

        result = invoke(
            [
                "agentic",
                "envoy",
                "enrollments",
                "list",
                "--campaign-id",
                CAMPAIGN_ID,
                "--state",
                "active",
            ]
        )

        assert result.exit_code == 2
        assert not route.called

    def test_evaluate_sends_the_request_id(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/enrollments/{ENROLLMENT_ID}/evaluate").respond(
            200,
            json={"enrollment": ENROLLMENT, "event_id": f"manual:{ENROLLMENT_ID}:r1"},
        )

        result = invoke(
            [
                "agentic",
                "envoy",
                "enrollments",
                "evaluate",
                ENROLLMENT_ID,
                "--request-id",
                "r1",
            ]
        )

        assert result.exit_code == 0, result.output
        assert _body(route) == {"request_id": "r1"}
        assert f"manual:{ENROLLMENT_ID}:r1" in result.output

    def test_evaluate_without_a_request_id_sends_an_empty_body(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/enrollments/{ENROLLMENT_ID}/evaluate").respond(
            200, json={"enrollment": ENROLLMENT, "event_id": "manual:x:y"}
        )

        result = invoke(["agentic", "envoy", "enrollments", "evaluate", ENROLLMENT_ID])

        assert result.exit_code == 0, result.output
        assert _body(route) == {}

    def test_exit_asks_first_and_then_posts(self, invoke, mock_api):
        ended = {**ENROLLMENT, "status": "ended", "ended_reason": "user_exit"}
        route = mock_api.post(f"{BASE}/enrollments/{ENROLLMENT_ID}/exit").respond(200, json=ended)

        refused = invoke(["agentic", "envoy", "enrollments", "exit", ENROLLMENT_ID], input="n\n")
        done = invoke(["agentic", "envoy", "enrollments", "exit", ENROLLMENT_ID, "--yes", "--json"])

        assert refused.exit_code == 1
        assert route.call_count == 1
        assert json.loads(done.output)["ended_reason"] == "user_exit"


class TestOrganization:
    def test_status_reads_the_stop(self, invoke, mock_api):
        mock_api.get(f"{BASE}/organization").respond(
            200, json={"stopped": False, "stopped_at": None}
        )

        result = invoke(["agentic", "envoy", "organization", "status", "--json"])

        assert json.loads(result.output) == {"stopped": False, "stopped_at": None}

    def test_stop_asks_first_and_then_posts(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/organization/stop").respond(200, json=STOP)

        refused = invoke(["agentic", "envoy", "organization", "stop"], input="n\n")
        done = invoke(["agentic", "envoy", "organization", "stop", "--yes"])

        assert refused.exit_code == 1
        assert done.exit_code == 0, done.output
        assert route.call_count == 1

    def test_resume_posts(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/organization/resume").respond(
            200, json={"stopped": False, "stopped_at": None}
        )

        result = invoke(["agentic", "envoy", "organization", "resume"])

        assert result.exit_code == 0, result.output
        assert route.called

    def test_a_member_gets_the_403_exit_code(self, invoke, mock_api):
        mock_api.post(f"{BASE}/organization/stop").respond(
            403, json={"detail": "only an organization admin stops or resumes Outreach"}
        )

        result = invoke(["agentic", "envoy", "organization", "stop", "--yes"])

        assert result.exit_code == 4


class TestJsonOutput:
    """Each command that answers a row prints it unchanged under --json."""

    def test_update_prints_json(self, invoke, mock_api):
        mock_api.patch(f"{BASE}/campaigns/{CAMPAIGN_ID}").respond(200, json=CAMPAIGN)

        result = invoke(
            ["agentic", "envoy", "campaigns", "update", CAMPAIGN_ID, "--name", "X", "--json"]
        )

        assert json.loads(result.output) == CAMPAIGN

    def test_enroll_prints_json(self, invoke, mock_api):
        mock_api.post(f"{BASE}/campaigns/{CAMPAIGN_ID}/enrollments").respond(201, json=ENROLLMENT)

        result = invoke(
            [
                "agentic",
                "envoy",
                "campaigns",
                "enroll",
                CAMPAIGN_ID,
                "--person-kind",
                "crm.person",
                "--person-id",
                PERSON_ID,
                "--json",
            ]
        )

        assert json.loads(result.output) == ENROLLMENT

    def test_enrollments_get_prints_json(self, invoke, mock_api):
        mock_api.get(f"{BASE}/enrollments/{ENROLLMENT_ID}").respond(200, json=ENROLLMENT)

        result = invoke(["agentic", "envoy", "enrollments", "get", ENROLLMENT_ID, "--json"])

        assert json.loads(result.output) == ENROLLMENT

    def test_evaluate_prints_json(self, invoke, mock_api):
        answer = {"enrollment": ENROLLMENT, "event_id": f"manual:{ENROLLMENT_ID}:r1"}
        mock_api.post(f"{BASE}/enrollments/{ENROLLMENT_ID}/evaluate").respond(200, json=answer)

        result = invoke(["agentic", "envoy", "enrollments", "evaluate", ENROLLMENT_ID, "--json"])

        assert json.loads(result.output) == answer

    def test_organization_stop_and_resume_print_json(self, invoke, mock_api):
        resumed = {"stopped": False, "stopped_at": None}
        mock_api.post(f"{BASE}/organization/stop").respond(200, json=STOP)
        mock_api.post(f"{BASE}/organization/resume").respond(200, json=resumed)

        stopped = invoke(["agentic", "envoy", "organization", "stop", "--yes", "--json"])
        cleared = invoke(["agentic", "envoy", "organization", "resume", "--json"])

        assert json.loads(stopped.output) == STOP
        assert json.loads(cleared.output) == resumed

    def test_a_409_under_json_carries_the_code(self, invoke, mock_api):
        mock_api.post(f"{BASE}/enrollments/{ENROLLMENT_ID}/evaluate").respond(
            409,
            json={
                "error": "Conflict",
                "message": "The enrollment waits for an email review.",
                "type": "conflict",
                "context": {"code": "awaiting_approval"},
                "code": "awaiting_approval",
            },
        )

        result = invoke(["agentic", "envoy", "enrollments", "evaluate", ENROLLMENT_ID, "--json"])

        body = json.loads(result.output)
        assert result.exit_code == 5
        assert (body["error"], body["status_code"]) == (True, 409)


TIMELINE = {
    "enrollment_id": ENROLLMENT_ID,
    "campaign_id": CAMPAIGN_ID,
    "campaign_name": "Q4 intro",
    "items": [
        {
            "kind": "ended",
            "at": "2026-10-23T09:00:00Z",
            "id": ENROLLMENT_ID,
            "ended_reason": "goal_met",
        },
        {
            "kind": "linkedin_message",
            "at": "2026-10-22T12:00:00Z",
            "id": "66666666-6666-4666-8666-666666666666",
            "direction": "inbound",
            "text": "Happy to chat.",
        },
        {
            "kind": "action",
            "at": "2026-10-22T10:00:00Z",
            "id": "77777777-7777-4777-8777-777777777777",
            "type": "email",
            "status": "rejected",
            "decision_id": "44444444-4444-4444-8444-444444444444",
            "communication_id": None,
            "reject_reason": "Too long.",
        },
        {
            "kind": "decision",
            "at": "2026-10-22T09:00:00Z",
            "id": "44444444-4444-4444-8444-444444444444",
            "type": "email",
            "status": "saved",
            "trigger_reason": "reply_received",
            "rationale": "She asked.",
            "objective": "Book a call.",
            "followup_days": 3,
            "goal_met": False,
            "failure_reason": None,
        },
        {
            "kind": "email",
            "at": "2026-10-21T15:00:00Z",
            "id": "55555555-5555-4555-8555-555555555555",
            "direction": "inbound",
            "subject": "Re: Hello",
            "status": "received",
            "text": "Can we talk on Friday?",
        },
        {
            "kind": "enrolled",
            "at": "2026-10-21T10:00:00Z",
            "id": ENROLLMENT_ID,
        },
    ],
}


class TestEnrollmentTimeline:
    def test_timeline_sends_the_limit_and_prints_each_kind(self, invoke, mock_api):
        route = mock_api.get(f"{BASE}/enrollments/{ENROLLMENT_ID}/timeline").respond(
            200, json=TIMELINE
        )

        result = invoke(
            ["agentic", "envoy", "enrollments", "timeline", ENROLLMENT_ID, "--limit", "5"]
        )

        assert result.exit_code == 0, result.output
        assert dict(route.calls[0].request.url.params) == {"limit": "5"}
        assert "Q4 intro" in result.output
        for line in (
            "goal_met",
            "inbound · Happy to chat.",
            "email · rejected · Too long.",
            "email · saved · She asked.",
            "inbound · received · Re: Hello",
            "linkedin_message",
            "action",
            "enrolled",
        ):
            assert line in result.output

    def test_timeline_has_no_order_option(self, invoke, mock_api):
        route = mock_api.get(f"{BASE}/enrollments/{ENROLLMENT_ID}/timeline")

        result = invoke(
            ["agentic", "envoy", "enrollments", "timeline", ENROLLMENT_ID, "--order", "asc"]
        )

        assert result.exit_code == 2
        assert not route.called

    def test_timeline_prints_json(self, invoke, mock_api):
        mock_api.get(f"{BASE}/enrollments/{ENROLLMENT_ID}/timeline").respond(200, json=TIMELINE)

        result = invoke(["agentic", "envoy", "enrollments", "timeline", ENROLLMENT_ID, "--json"])

        assert json.loads(result.output) == TIMELINE

    def test_timeline_refuses_a_bad_limit_without_a_call(self, invoke, mock_api):
        route = mock_api.get(f"{BASE}/enrollments/{ENROLLMENT_ID}/timeline")

        result = invoke(
            ["agentic", "envoy", "enrollments", "timeline", ENROLLMENT_ID, "--limit", "101"]
        )

        assert result.exit_code == 2
        assert not route.called

    def test_timeline_of_an_unknown_enrollment_gets_the_404_exit_code(self, invoke, mock_api):
        mock_api.get(f"{BASE}/enrollments/{ENROLLMENT_ID}/timeline").respond(
            404, json={"detail": "Outreach enrollment not found"}
        )

        result = invoke(["agentic", "envoy", "enrollments", "timeline", ENROLLMENT_ID])

        assert result.exit_code == 3

    def test_timeline_without_a_campaign_name_prints_no_none(self, invoke, mock_api):
        mock_api.get(f"{BASE}/enrollments/{ENROLLMENT_ID}/timeline").respond(
            200, json={**TIMELINE, "campaign_name": None}
        )

        result = invoke(["agentic", "envoy", "enrollments", "timeline", ENROLLMENT_ID])

        assert result.exit_code == 0, result.output
        assert "None" not in result.output


LIST = ["agentic", "envoy", "enrollments", "list", "--campaign-id", CAMPAIGN_ID]


def _page(rows, *, total, offset, has_more, limit=100):
    return {"data": rows, "total": total, "limit": limit, "offset": offset, "has_more": has_more}


def test_list_prints_a_row_with_no_decision_and_no_name_as_blank(invoke, mock_api, table_column):
    """`_with_last_action` returns the row as it is when last_decision is None."""
    bare = {**ENROLLMENT, "person_name": None, "email": None, "last_decision": None}
    mock_api.get(f"{BASE}/campaigns/{CAMPAIGN_ID}/enrollments").respond(
        200, json=_page([bare], total=1, offset=0, has_more=False)
    )

    result = invoke(LIST)

    assert result.exit_code == 0, result.output
    assert "None" not in result.output
    assert table_column(result.output, 1) == ""
    assert table_column(result.output, 4) == ""
    assert "Envoy enrollments 1-1 of 1" in result.output
    assert "--offset" not in result.output


def test_list_names_only_the_status_of_a_decision_without_a_type(invoke, mock_api, table_column):
    row = {
        **ROW,
        "last_decision": {**ROW["last_decision"], "type": None, "status": "error"},
    }
    mock_api.get(f"{BASE}/campaigns/{CAMPAIGN_ID}/enrollments").respond(
        200, json=_page([row], total=1, offset=0, has_more=False)
    )

    result = invoke(LIST)

    assert result.exit_code == 0, result.output
    assert table_column(result.output, 4) == "error"
    assert "·" not in result.output


def test_list_past_the_end_prints_zero_of_the_total_and_no_next_offset(invoke, mock_api):
    mock_api.get(f"{BASE}/campaigns/{CAMPAIGN_ID}/enrollments").respond(
        200, json=_page([], total=3, offset=10, has_more=False)
    )

    result = invoke([*LIST, "--offset", "10"])

    assert result.exit_code == 0, result.output
    assert "Envoy enrollments 0 of 3" in result.output
    assert "--offset" not in result.output


def test_timeline_says_newest_first_and_sends_no_order(invoke, mock_api):
    route = mock_api.get(f"{BASE}/enrollments/{ENROLLMENT_ID}/timeline").respond(200, json=TIMELINE)

    result = invoke(["agentic", "envoy", "enrollments", "timeline", ENROLLMENT_ID])

    assert result.exit_code == 0, result.output
    assert "order" not in route.calls[0].request.url.params
    assert "newest first" in result.output


def test_get_of_a_campaign_without_counts_prints_no_none(invoke, mock_api):
    mock_api.get(f"{BASE}/campaigns/{CAMPAIGN_ID}").respond(200, json=CAMPAIGN)

    result = invoke(["agentic", "envoy", "campaigns", "get", CAMPAIGN_ID])

    assert result.exit_code == 0, result.output
    assert "None" not in result.output
    assert "Q4 intro" in result.output

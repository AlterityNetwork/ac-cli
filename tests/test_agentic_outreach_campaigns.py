"""Tests for the Outreach campaign, enrollment and organization stop commands."""

import json

BASE = "/api/v1/agentic/outreach"
CAMPAIGN_ID = "33333333-3333-4333-8333-333333333333"
ENROLLMENT_ID = "22222222-2222-4222-8222-222222222222"
PERSON_ID = "77777777-7777-4777-8777-777777777777"
PLAYBOOK_ID = "88888888-8888-4888-8888-888888888888"

CAMPAIGN = {
    "id": CAMPAIGN_ID,
    "name": "Q4 intro",
    "status": "draft",
    "goal": "Book a call",
    "instructions": "",
    "max_emails": 3,
    "min_days_between_emails": 3,
    "writing_style_id": None,
    "playbook_id": None,
    "battlecard_id": None,
    "created_by": "99999999-9999-4999-8999-999999999999",
    "created_at": "2026-10-21T10:00:00Z",
    "updated_at": "2026-10-21T10:00:00Z",
}
ENROLLMENT = {
    "id": ENROLLMENT_ID,
    "campaign_id": CAMPAIGN_ID,
    "person_kind": "crm.person",
    "person_id": PERSON_ID,
    "state": "active",
    "ended_reason": None,
    "next_due_at": None,
    "active_run_id": None,
    "version": 0,
    "enrolled_at": "2026-10-21T10:00:00Z",
    "ended_at": None,
    "updated_at": "2026-10-21T10:00:00Z",
}
STOP = {"stopped": True, "stopped_at": "2026-10-21T10:00:00Z"}


def _body(route) -> dict:
    return json.loads(route.calls[0].request.content)


class TestCampaigns:
    def test_list_sends_the_filters(self, invoke, mock_api):
        route = mock_api.get(f"{BASE}/campaigns").respond(200, json={"items": [CAMPAIGN]})

        result = invoke(
            ["agentic", "outreach", "campaigns", "list", "--status", "draft", "--limit", "5"]
        )

        assert result.exit_code == 0, result.output
        params = route.calls[0].request.url.params
        assert (params["status"], params["limit"]) == ("draft", "5")
        assert "Q4 intro" in result.output

    def test_list_refuses_a_bad_status_without_a_call(self, invoke, mock_api):
        route = mock_api.get(f"{BASE}/campaigns").respond(200, json={"items": []})

        result = invoke(["agentic", "outreach", "campaigns", "list", "--status", "live"])

        assert result.exit_code == 2
        assert not route.called

    def test_get_prints_the_campaign(self, invoke, mock_api):
        mock_api.get(f"{BASE}/campaigns/{CAMPAIGN_ID}").respond(200, json=CAMPAIGN)

        result = invoke(["agentic", "outreach", "campaigns", "get", CAMPAIGN_ID, "--json"])

        assert json.loads(result.output) == CAMPAIGN

    def test_create_sends_only_the_given_fields(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/campaigns").respond(201, json=CAMPAIGN)

        result = invoke(
            [
                "agentic",
                "outreach",
                "campaigns",
                "create",
                "--name",
                "Q4 intro",
                "--goal",
                "Book a call",
                "--max-emails",
                "2",
                "--playbook-id",
                PLAYBOOK_ID,
            ]
        )

        assert result.exit_code == 0, result.output
        assert _body(route) == {
            "name": "Q4 intro",
            "goal": "Book a call",
            "max_emails": 2,
            "playbook_id": PLAYBOOK_ID,
        }

    def test_update_clears_a_link_with_none(self, invoke, mock_api):
        route = mock_api.patch(f"{BASE}/campaigns/{CAMPAIGN_ID}").respond(200, json=CAMPAIGN)

        result = invoke(
            [
                "agentic",
                "outreach",
                "campaigns",
                "update",
                CAMPAIGN_ID,
                "--min-days",
                "5",
                "--writing-style-id",
                "none",
            ]
        )

        assert result.exit_code == 0, result.output
        assert _body(route) == {"min_days_between_emails": 5, "writing_style_id": None}

    def test_update_with_nothing_refuses_without_a_call(self, invoke, mock_api):
        route = mock_api.patch(f"{BASE}/campaigns/{CAMPAIGN_ID}").respond(200, json=CAMPAIGN)

        result = invoke(["agentic", "outreach", "campaigns", "update", CAMPAIGN_ID])

        assert result.exit_code == 2
        assert not route.called

    def test_each_status_command_posts_its_status(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/campaigns/{CAMPAIGN_ID}/status").respond(200, json=CAMPAIGN)

        for command, status in (
            ("activate", "active"),
            ("pause", "paused"),
            ("resume", "active"),
            ("archive", "archived"),
        ):
            args = ["agentic", "outreach", "campaigns", command, CAMPAIGN_ID]
            result = invoke([*args, "--yes"] if command == "archive" else args)
            assert result.exit_code == 0, result.output
            assert json.loads(route.calls[-1].request.content) == {"status": status}

    def test_each_status_command_prints_json(self, invoke, mock_api):
        mock_api.post(f"{BASE}/campaigns/{CAMPAIGN_ID}/status").respond(200, json=CAMPAIGN)

        for command in ("activate", "pause", "resume", "archive"):
            args = ["agentic", "outreach", "campaigns", command, CAMPAIGN_ID, "--json"]
            result = invoke([*args, "--yes"] if command == "archive" else args)
            assert json.loads(result.output) == CAMPAIGN

    def test_list_and_create_print_json(self, invoke, mock_api):
        mock_api.get(f"{BASE}/campaigns").respond(200, json={"items": [CAMPAIGN]})
        mock_api.post(f"{BASE}/campaigns").respond(201, json=CAMPAIGN)

        listed = invoke(["agentic", "outreach", "campaigns", "list", "--json"])
        created = invoke(["agentic", "outreach", "campaigns", "create", "--name", "X", "--json"])

        assert json.loads(listed.output) == {"items": [CAMPAIGN]}
        assert json.loads(created.output) == CAMPAIGN

    def test_counts_out_of_range_are_refused_without_a_call(self, invoke, mock_api):
        create = mock_api.post(f"{BASE}/campaigns").respond(201, json=CAMPAIGN)
        update = mock_api.patch(f"{BASE}/campaigns/{CAMPAIGN_ID}").respond(200, json=CAMPAIGN)

        for args in (
            ["create", "--name", "X", "--max-emails", "21"],
            ["create", "--name", "X", "--min-days", "0"],
            ["update", CAMPAIGN_ID, "--max-emails", "0"],
            ["update", CAMPAIGN_ID, "--min-days", "31", "--json"],
        ):
            result = invoke(["agentic", "outreach", "campaigns", *args])
            assert result.exit_code == 2, args
        assert not create.called
        assert not update.called

    def test_archive_asks_first(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/campaigns/{CAMPAIGN_ID}/status").respond(200, json=CAMPAIGN)

        result = invoke(["agentic", "outreach", "campaigns", "archive", CAMPAIGN_ID], input="n\n")

        assert result.exit_code == 1
        assert not route.called

    def test_enroll_posts_the_person(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/campaigns/{CAMPAIGN_ID}/enrollments").respond(
            201, json=ENROLLMENT
        )

        result = invoke(
            [
                "agentic",
                "outreach",
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
                "outreach",
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

    def test_enroll_refuses_a_bad_person_kind_without_a_call(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/campaigns/{CAMPAIGN_ID}/enrollments").respond(
            201, json=ENROLLMENT
        )

        result = invoke(
            [
                "agentic",
                "outreach",
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
    def test_list_reads_one_campaign(self, invoke, mock_api):
        route = mock_api.get(f"{BASE}/campaigns/{CAMPAIGN_ID}/enrollments").respond(
            200, json={"items": [ENROLLMENT]}
        )

        result = invoke(
            [
                "agentic",
                "outreach",
                "enrollments",
                "list",
                "--campaign-id",
                CAMPAIGN_ID,
                "--state",
                "active",
            ]
        )

        assert result.exit_code == 0, result.output
        assert route.calls[0].request.url.params["state"] == "active"
        assert "Outreach enrollments" in result.output

    def test_list_json_keeps_the_page(self, invoke, mock_api):
        mock_api.get(f"{BASE}/campaigns/{CAMPAIGN_ID}/enrollments").respond(
            200, json={"items": [ENROLLMENT]}
        )

        result = invoke(
            ["agentic", "outreach", "enrollments", "list", "--campaign-id", CAMPAIGN_ID, "--json"]
        )

        assert json.loads(result.output) == {"items": [ENROLLMENT]}

    def test_list_refuses_a_bad_limit_without_a_call(self, invoke, mock_api):
        route = mock_api.get(f"{BASE}/campaigns/{CAMPAIGN_ID}/enrollments").respond(
            200, json={"items": []}
        )

        result = invoke(
            [
                "agentic",
                "outreach",
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

        result = invoke(["agentic", "outreach", "enrollments", "get", ENROLLMENT_ID])

        assert result.exit_code == 0, result.output
        assert "crm.person" in result.output

    def test_evaluate_sends_the_request_id(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/enrollments/{ENROLLMENT_ID}/evaluate").respond(
            200,
            json={"enrollment": ENROLLMENT, "event_id": f"manual:{ENROLLMENT_ID}:r1"},
        )

        result = invoke(
            [
                "agentic",
                "outreach",
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

        result = invoke(["agentic", "outreach", "enrollments", "evaluate", ENROLLMENT_ID])

        assert result.exit_code == 0, result.output
        assert _body(route) == {}

    def test_exit_asks_first_and_then_posts(self, invoke, mock_api):
        ended = {**ENROLLMENT, "state": "ended", "ended_reason": "manual"}
        route = mock_api.post(f"{BASE}/enrollments/{ENROLLMENT_ID}/exit").respond(200, json=ended)

        refused = invoke(["agentic", "outreach", "enrollments", "exit", ENROLLMENT_ID], input="n\n")
        done = invoke(
            ["agentic", "outreach", "enrollments", "exit", ENROLLMENT_ID, "--yes", "--json"]
        )

        assert refused.exit_code == 1
        assert route.call_count == 1
        assert json.loads(done.output)["ended_reason"] == "manual"


class TestOrganization:
    def test_status_reads_the_stop(self, invoke, mock_api):
        mock_api.get(f"{BASE}/organization").respond(
            200, json={"stopped": False, "stopped_at": None}
        )

        result = invoke(["agentic", "outreach", "organization", "status", "--json"])

        assert json.loads(result.output) == {"stopped": False, "stopped_at": None}

    def test_stop_asks_first_and_then_posts(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/organization/stop").respond(200, json=STOP)

        refused = invoke(["agentic", "outreach", "organization", "stop"], input="n\n")
        done = invoke(["agentic", "outreach", "organization", "stop", "--yes"])

        assert refused.exit_code == 1
        assert done.exit_code == 0, done.output
        assert route.call_count == 1

    def test_resume_posts(self, invoke, mock_api):
        route = mock_api.post(f"{BASE}/organization/resume").respond(
            200, json={"stopped": False, "stopped_at": None}
        )

        result = invoke(["agentic", "outreach", "organization", "resume"])

        assert result.exit_code == 0, result.output
        assert route.called

    def test_a_member_gets_the_403_exit_code(self, invoke, mock_api):
        mock_api.post(f"{BASE}/organization/stop").respond(
            403, json={"detail": "only an organization admin stops or resumes Outreach"}
        )

        result = invoke(["agentic", "outreach", "organization", "stop", "--yes"])

        assert result.exit_code == 4


class TestJsonOutput:
    """Each command that answers a row prints it unchanged under --json."""

    def test_update_prints_json(self, invoke, mock_api):
        mock_api.patch(f"{BASE}/campaigns/{CAMPAIGN_ID}").respond(200, json=CAMPAIGN)

        result = invoke(
            ["agentic", "outreach", "campaigns", "update", CAMPAIGN_ID, "--name", "X", "--json"]
        )

        assert json.loads(result.output) == CAMPAIGN

    def test_enroll_prints_json(self, invoke, mock_api):
        mock_api.post(f"{BASE}/campaigns/{CAMPAIGN_ID}/enrollments").respond(201, json=ENROLLMENT)

        result = invoke(
            [
                "agentic",
                "outreach",
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

        result = invoke(["agentic", "outreach", "enrollments", "get", ENROLLMENT_ID, "--json"])

        assert json.loads(result.output) == ENROLLMENT

    def test_evaluate_prints_json(self, invoke, mock_api):
        answer = {"enrollment": ENROLLMENT, "event_id": f"manual:{ENROLLMENT_ID}:r1"}
        mock_api.post(f"{BASE}/enrollments/{ENROLLMENT_ID}/evaluate").respond(200, json=answer)

        result = invoke(["agentic", "outreach", "enrollments", "evaluate", ENROLLMENT_ID, "--json"])

        assert json.loads(result.output) == answer

    def test_organization_stop_and_resume_print_json(self, invoke, mock_api):
        resumed = {"stopped": False, "stopped_at": None}
        mock_api.post(f"{BASE}/organization/stop").respond(200, json=STOP)
        mock_api.post(f"{BASE}/organization/resume").respond(200, json=resumed)

        stopped = invoke(["agentic", "outreach", "organization", "stop", "--yes", "--json"])
        cleared = invoke(["agentic", "outreach", "organization", "resume", "--json"])

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

        result = invoke(["agentic", "outreach", "enrollments", "evaluate", ENROLLMENT_ID, "--json"])

        body = json.loads(result.output)
        assert result.exit_code == 5
        assert (body["error"], body["status_code"]) == (True, 409)


TIMELINE = {
    "enrollment_id": ENROLLMENT_ID,
    "campaign_id": CAMPAIGN_ID,
    "campaign_name": "Q4 intro",
    "items": [
        {
            "kind": "decision",
            "at": "2026-10-22T09:00:00Z",
            "id": "44444444-4444-4444-8444-444444444444",
            "action_type": "send_email",
            "outcome": "proposed",
            "reason": "Jane asked for a call.",
            "reviewer_note": None,
            "failure_code": None,
            "subject": "A time for the call",
            "direction": None,
            "status": None,
            "activity_type": None,
            "title": None,
            "ended_reason": None,
        },
        {
            "kind": "email",
            "at": "2026-10-21T15:00:00Z",
            "id": "55555555-5555-4555-8555-555555555555",
            "action_type": None,
            "outcome": None,
            "reason": None,
            "reviewer_note": None,
            "failure_code": None,
            "subject": "Re: Hello Jane",
            "direction": "inbound",
            "status": "received",
            "activity_type": None,
            "title": None,
            "ended_reason": None,
        },
        {
            "kind": "enrolled",
            "at": "2026-10-21T10:00:00Z",
            "id": None,
            "action_type": None,
            "outcome": None,
            "reason": None,
            "reviewer_note": None,
            "failure_code": None,
            "subject": None,
            "direction": None,
            "status": None,
            "activity_type": None,
            "title": None,
            "ended_reason": None,
        },
    ],
}


class TestEnrollmentTimeline:
    def test_timeline_sends_the_limit_and_prints_each_fact(self, invoke, mock_api):
        route = mock_api.get(f"{BASE}/enrollments/{ENROLLMENT_ID}/timeline").respond(
            200, json=TIMELINE
        )

        result = invoke(
            ["agentic", "outreach", "enrollments", "timeline", ENROLLMENT_ID, "--limit", "5"]
        )

        assert result.exit_code == 0, result.output
        assert route.calls[0].request.url.params["limit"] == "5"
        assert "Q4 intro" in result.output
        assert "proposed" in result.output
        assert "Re: Hello Jane" in result.output
        assert "enrolled" in result.output

    def test_timeline_prints_json(self, invoke, mock_api):
        mock_api.get(f"{BASE}/enrollments/{ENROLLMENT_ID}/timeline").respond(200, json=TIMELINE)

        result = invoke(["agentic", "outreach", "enrollments", "timeline", ENROLLMENT_ID, "--json"])

        assert json.loads(result.output) == TIMELINE

    def test_timeline_refuses_a_bad_limit_without_a_call(self, invoke, mock_api):
        route = mock_api.get(f"{BASE}/enrollments/{ENROLLMENT_ID}/timeline")

        result = invoke(
            ["agentic", "outreach", "enrollments", "timeline", ENROLLMENT_ID, "--limit", "101"]
        )

        assert result.exit_code == 2
        assert not route.called

    def test_timeline_of_an_unknown_enrollment_gets_the_404_exit_code(self, invoke, mock_api):
        mock_api.get(f"{BASE}/enrollments/{ENROLLMENT_ID}/timeline").respond(
            404, json={"detail": "Outreach enrollment not found"}
        )

        result = invoke(["agentic", "outreach", "enrollments", "timeline", ENROLLMENT_ID])

        assert result.exit_code == 3

    def test_timeline_without_a_campaign_name_prints_no_none(self, invoke, mock_api):
        mock_api.get(f"{BASE}/enrollments/{ENROLLMENT_ID}/timeline").respond(
            200, json={**TIMELINE, "campaign_name": None}
        )

        result = invoke(["agentic", "outreach", "enrollments", "timeline", ENROLLMENT_ID])

        assert result.exit_code == 0, result.output
        assert "None" not in result.output

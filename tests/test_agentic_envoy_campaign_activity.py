"""Tests for `ac agentic envoy campaigns activity` and `campaigns results`."""

import json

BASE = "/api/v1/agentic/envoy"
CAMPAIGN_ID = "33333333-3333-4333-8333-333333333333"
ENROLLMENT_ID = "22222222-2222-4222-8222-222222222222"
PERSON_ID = "77777777-7777-4777-8777-777777777777"


def _item(kind: str, **fields: object) -> dict:
    item = {
        "kind": kind,
        "at": "2026-11-10T09:00:00Z",
        "id": "44444444-4444-4444-8444-444444444444",
        "enrollment_id": ENROLLMENT_ID,
        "person": {"kind": "crm.person", "id": PERSON_ID, "name": "Hannah Okafor"},
        "channel": "email",
        "type": "email",
        "status": "executed",
        "trigger_reason": "followup_due",
        "rationale": None,
        "objective": None,
        "followup_days": None,
        "goal_met": None,
        "subject": None,
    }
    return {**item, **fields}


ACTIVITY = {
    "items": [
        _item(
            "decision",
            channel=None,
            type="wait",
            status="saved",
            rationale="No answer [yet].",
        ),
        _item("reply", trigger_reason="reply_received", status="saved"),
        _item("send", subject="Quick question"),
        _item("send", person={"kind": "prospect.person", "id": PERSON_ID, "name": None}),
    ],
    "next_cursor": "MjAyNi0xMS0xMFQwOTowMDowMCswMDowMHw0NDQ0",
}
RESULTS = {
    "from": "2026-11-12",
    "to": "2026-11-14",
    "sends_per_day": [
        {"day": "2026-11-12", "email": 2, "linkedin": 0},
        {"day": "2026-11-13", "email": 0, "linkedin": 0},
        {"day": "2026-11-14", "email": 1, "linkedin": 3},
    ],
    "by_touch": [
        {"touch": 1, "sends": 8, "replies": 2, "reply_rate": 0.25},
        {"touch": 2, "sends": 3, "replies": 0, "reply_rate": 0.0},
    ],
    "truncated": False,
}
ACTIVITY_CMD = ["agentic", "envoy", "campaigns", "activity", CAMPAIGN_ID]
RESULTS_CMD = ["agentic", "envoy", "campaigns", "results", CAMPAIGN_ID]


class TestCampaignActivity:
    def test_activity_sends_the_filters_and_prints_who_and_what(self, invoke, mock_api):
        route = mock_api.get(f"{BASE}/campaigns/{CAMPAIGN_ID}/activity").respond(200, json=ACTIVITY)

        result = invoke(
            [
                *ACTIVITY_CMD,
                "--kind",
                "send",
                "--channel",
                "email",
                "--limit",
                "4",
                "--cursor",
                "abc",
            ]
        )

        assert result.exit_code == 0, result.output
        assert dict(route.calls[0].request.url.params) == {
            "kind": "send",
            "channel": "email",
            "limit": "4",
            "cursor": "abc",
        }
        for text in (
            "Hannah Okafor",
            "Email sent · Quick question",
            "Reply received",
            "Decided wait · No answer [yet].",
            "2026-11-10 09:00",
            "--cursor " + ACTIVITY["next_cursor"],
        ):
            assert text in result.output
        assert "None" not in result.output

    def test_activity_sends_only_the_limit_by_default(self, invoke, mock_api):
        route = mock_api.get(f"{BASE}/campaigns/{CAMPAIGN_ID}/activity").respond(
            200, json={"items": [], "next_cursor": None}
        )

        result = invoke(ACTIVITY_CMD)

        assert result.exit_code == 0, result.output
        assert dict(route.calls[0].request.url.params) == {"limit": "50"}
        assert "--cursor" not in result.output

    def test_activity_prints_json(self, invoke, mock_api):
        mock_api.get(f"{BASE}/campaigns/{CAMPAIGN_ID}/activity").respond(200, json=ACTIVITY)

        result = invoke([*ACTIVITY_CMD, "--json"])

        assert json.loads(result.output) == ACTIVITY

    def test_activity_refuses_a_bad_filter_without_a_call(self, invoke, mock_api):
        route = mock_api.get(f"{BASE}/campaigns/{CAMPAIGN_ID}/activity")

        for flags in (["--kind", "email"], ["--channel", "sms"], ["--limit", "101"]):
            result = invoke([*ACTIVITY_CMD, *flags])
            assert result.exit_code == 2, flags

        assert not route.called

    def test_activity_of_an_unknown_campaign_gets_the_404_exit_code(self, invoke, mock_api):
        mock_api.get(f"{BASE}/campaigns/{CAMPAIGN_ID}/activity").respond(
            404, json={"detail": "Envoy campaign not found"}
        )

        assert invoke(ACTIVITY_CMD).exit_code == 3


class TestCampaignResults:
    def test_results_send_the_days_and_print_both_tables(self, invoke, mock_api):
        route = mock_api.get(f"{BASE}/campaigns/{CAMPAIGN_ID}/results").respond(200, json=RESULTS)

        result = invoke([*RESULTS_CMD, "--days", "3"])

        assert result.exit_code == 0, result.output
        assert dict(route.calls[0].request.url.params) == {"days": "3"}
        for text in ("2026-11-12", "2026-11-14", "25.0%", "Touch", "Sends per day"):
            assert text in result.output
        assert "only the newest" not in result.output

    def test_results_say_when_the_scan_stopped_at_its_cap(self, invoke, mock_api):
        mock_api.get(f"{BASE}/campaigns/{CAMPAIGN_ID}/results").respond(
            200, json={**RESULTS, "truncated": True}
        )

        result = invoke(RESULTS_CMD)

        assert result.exit_code == 0, result.output
        assert "only the newest" in result.output

    def test_results_send_30_days_by_default(self, invoke, mock_api):
        route = mock_api.get(f"{BASE}/campaigns/{CAMPAIGN_ID}/results").respond(200, json=RESULTS)

        invoke(RESULTS_CMD)

        assert dict(route.calls[0].request.url.params) == {"days": "30"}

    def test_results_print_json(self, invoke, mock_api):
        mock_api.get(f"{BASE}/campaigns/{CAMPAIGN_ID}/results").respond(200, json=RESULTS)

        result = invoke([*RESULTS_CMD, "--json"])

        assert json.loads(result.output) == RESULTS

    def test_results_refuse_days_out_of_range_without_a_call(self, invoke, mock_api):
        route = mock_api.get(f"{BASE}/campaigns/{CAMPAIGN_ID}/results")

        for days in ("0", "91"):
            assert invoke([*RESULTS_CMD, "--days", days]).exit_code == 2

        assert not route.called

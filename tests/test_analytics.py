"""Tests for analytics commands."""

import json

import pytest

OVERVIEW = {
    "start_date": "2026-06-21",
    "end_date": "2026-07-21",
    "period_days": 30,
    "prospects_found": {"current": 42, "previous": 30, "change_pct": 40.0},
    "prospects_watched": {"current": 9, "previous": 6, "change_pct": 50.0},
    "prospects_watching_total": 14,
    "prospects_dismissed": {"current": 11, "previous": 8, "change_pct": 37.5},
    "signals_searches": {"current": 12, "previous": 9, "change_pct": 33.3},
    "signals_searches_saved": 9,
    "prospects_pursued_rate": {"current": 14.3, "previous": 10.0, "change_pct": 43.0},
    "prospects_pursued": {"current": 6, "previous": 2, "change_pct": 200.0},
    "sequences_active": 4,
    "sequence_prospects_added": {"current": 50, "previous": 40, "change_pct": 25.0},
    "outbound_touches": {"current": 240, "previous": 180, "change_pct": 33.3},
    "replies": {"current": 12, "previous": 9, "change_pct": 33.3},
    "avg_reply_hours": {"current": 30.5, "previous": 40.0, "change_pct": -23.8},
    "sequence_emails_sent": {"current": 80, "previous": 60, "change_pct": 33.3},
    "email_reply_rate": {"current": 8.5, "previous": 6.0, "change_pct": 41.7},
    "email_positive_reply_rate": {"current": 3.0, "previous": 2.0, "change_pct": 50.0},
    "email_bounce_rate": {"current": 1.2, "previous": 2.4, "change_pct": -50.0},
    "linkedin_requests_sent": {"current": 20, "previous": 16, "change_pct": 25.0},
    "linkedin_requests_accepted": {"current": 7, "previous": 5, "change_pct": 40.0},
    "linkedin_acceptance_rate": {"current": 35.0, "previous": 50.0, "change_pct": -30.0},
    "linkedin_requests_awaiting": {"current": 9, "previous": 2, "change_pct": 350.0},
    "linkedin_requests_by_day": [{"date": "2026-07-21", "sent": 5, "accepted": 2}],
    "sequences_by_reply_rate": [
        {
            "id": "s1",
            "name": "Q4 founders",
            "status": "active",
            "prospects": 40,
            "replies": 5,
            "reply_rate": 12.5,
        }
    ],
    "sequences_processed_by_day": [],
    "outputs_by_type": [{"type": "Email", "count": 240}],
    "companies_new": {"current": 15, "previous": 10, "change_pct": 50.0},
    "companies_total": 300,
    "people": {"current": 40, "previous": 35, "change_pct": 14.3},
    "people_total": 900,
    "tasks_created": {"current": 20, "previous": 18, "change_pct": 11.1},
    "tasks_completed": {"current": 16, "previous": 12, "change_pct": 33.3},
    "tasks_created_completed": 14,
    "task_completion_rate": 70.588,
    "workflow_runs": {"current": 9, "previous": 7, "change_pct": 28.6},
    "logins": {"current": 55, "previous": 50, "change_pct": 10.0},
    "active_users": {"current": 4, "previous": 4, "change_pct": 0.0},
    "daily_activity": [],
}


def test_analytics_overview(invoke, mock_api):
    mock_api.get("/api/v1/analytics/overview").respond(200, json=OVERVIEW)
    result = invoke(["analytics", "overview"])
    assert result.exit_code == 0
    assert "Prospects found" in result.output
    assert "Outbound touches" in result.output
    assert "42" in result.output
    assert "2026-06-21" in result.output
    assert "Live sequences: 4" in result.output
    assert "Watching now: 14" in result.output
    assert "Task completion rate: 70.6%" in result.output
    assert "Sequences by reply rate" in result.output
    assert "Q4 founders" in result.output
    assert "12.5%" in result.output
    assert "Sonar" not in result.output
    assert "Headhunter" not in result.output
    assert "Reply rate:" not in result.output
    assert "Signals searches" in result.output
    assert "Saved searches: 9 of 12 (75.0%)" in result.output
    assert "Prospects pursued: 14.3% of the prospects found" in result.output
    assert "Average time to reply: 30.5 hours" in result.output
    assert "Sequence emails sent" in result.output
    assert "Email reply rate: 8.5%" in result.output
    assert "Positive reply rate: 3.0%" in result.output
    assert "Bounce rate: 1.2%" in result.output
    assert "added to CRM" not in result.output


def test_analytics_overview_shows_the_linkedin_requests(invoke, mock_api):
    mock_api.get("/api/v1/analytics/overview").respond(200, json=OVERVIEW)
    result = invoke(["analytics", "overview"])
    assert result.exit_code == 0
    assert "LinkedIn requests sent" in result.output
    assert "LinkedIn requests accepted" in result.output
    assert "LinkedIn requests awaiting acceptance" in result.output
    assert "LinkedIn acceptance rate: 35.0%" in result.output


def test_analytics_overview_period_days(invoke, mock_api):
    route = mock_api.get("/api/v1/analytics/overview").respond(200, json=OVERVIEW)
    result = invoke(["analytics", "overview", "--period-days", "7"])
    assert result.exit_code == 0
    assert route.calls.last.request.url.params["period_days"] == "7"


def test_analytics_overview_rejects_out_of_range_period_before_request(invoke, mock_api):
    result = invoke(["analytics", "overview", "--period-days", "366"])
    assert result.exit_code == 2
    assert not mock_api.calls


def test_analytics_overview_json(invoke, mock_api):
    mock_api.get("/api/v1/analytics/overview").respond(200, json=OVERVIEW)
    result = invoke(["analytics", "overview", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output) == OVERVIEW


def test_analytics_overview_error(invoke, mock_api):
    mock_api.get("/api/v1/analytics/overview").respond(500, json={"detail": "boom"})
    result = invoke(["analytics", "overview"])
    assert result.exit_code == 1


def test_analytics_overview_error_json(invoke, mock_api):
    mock_api.get("/api/v1/analytics/overview").respond(500, json={"detail": "boom"})
    result = invoke(["analytics", "overview", "--json"])
    assert result.exit_code == 1
    body = json.loads(result.output)
    assert body["error"] is True
    assert body["status_code"] == 500
    assert body["detail"] == "boom"


def test_analytics_overview_renders_null_change_without_crashing(invoke, mock_api):
    """The API sends change_pct: null when the previous period was zero.

    `.get("change_pct", 0.0)` returns None for a present-but-null key, and
    f"{None:+.1f}%" raises TypeError — so the whole command died on any org
    whose metric grew from nothing.
    """
    payload = dict(OVERVIEW)
    payload["prospects_found"] = {"current": 42, "previous": 0, "change_pct": None}

    mock_api.get("/api/v1/analytics/overview").respond(200, json=payload)
    result = invoke(["analytics", "overview"])

    assert result.exit_code == 0
    assert "Prospects found" in result.output
    # No fabricated percentage for an undefined comparison.
    assert "+100.0%" not in result.output


def test_analytics_overview_json_passes_null_change_through(invoke, mock_api):
    payload = dict(OVERVIEW)
    payload["prospects_found"] = {"current": 42, "previous": 0, "change_pct": None}

    mock_api.get("/api/v1/analytics/overview").respond(200, json=payload)
    result = invoke(["analytics", "overview", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output)["prospects_found"]["change_pct"] is None


def test_analytics_overview_with_no_sequences_prints_no_ranking(invoke, mock_api):
    payload = dict(OVERVIEW)
    payload["sequences_by_reply_rate"] = []

    mock_api.get("/api/v1/analytics/overview").respond(200, json=payload)
    result = invoke(["analytics", "overview"])

    assert result.exit_code == 0
    assert "Sequences by reply rate" not in result.output


def test_analytics_overview_without_searches_or_replies(invoke, mock_api):
    empty = {
        **OVERVIEW,
        "signals_searches": {"current": 0, "previous": 0, "change_pct": 0.0},
        "signals_searches_saved": 0,
        "prospects_pursued_rate": {"current": None, "previous": None, "change_pct": None},
        "avg_reply_hours": {"current": None, "previous": None, "change_pct": None},
        "email_reply_rate": {"current": None, "previous": None, "change_pct": None},
        "linkedin_acceptance_rate": {
            "current": None,
            "previous": None,
            "change_pct": None,
        },
    }
    mock_api.get("/api/v1/analytics/overview").respond(200, json=empty)
    result = invoke(["analytics", "overview"])
    assert result.exit_code == 0
    assert "LinkedIn acceptance rate: -" in result.output
    assert "Saved searches: 0 of 0" in result.output
    assert "Prospects pursued: -" in result.output
    assert "Average time to reply: -" in result.output
    assert "Email reply rate: -" in result.output


_CATEGORIES = {
    "interested": 1,
    "referral": 0,
    "out_of_office": 1,
    "unclear": 1,
    "not_interested": 0,
    "opted_out": 0,
}

REPLIES = {
    "start_date": "2026-06-21",
    "end_date": "2026-07-21",
    "period_days": 30,
    "scope": "replies",
    "channel": None,
    "category": None,
    "total": 3,
    "by_category": _CATEGORIES,
    "touches_by_category": None,
    "items": [
        {
            "recipient_id": "r1",
            "person_id": "p1",
            "person_name": "Ann Lee",
            "company_id": "c1",
            "company_name": "Acme [beta]",
            "sequence_id": "s1",
            "sequence_name": "Q4 founders",
            "channel": "email",
            "category": "interested",
            "intent_source": "model",
            "excerpt": "Yes, send me the price.",
            "replied_at": "2026-07-20T09:00:00+00:00",
            "communication_id": "m1",
            "inbox_thread_id": "t1",
            "touches": 2,
        },
        {
            "recipient_id": "r2",
            "person_id": "p2",
            "person_name": "Bo Kim",
            "company_id": None,
            "company_name": None,
            "sequence_id": "s1",
            "sequence_name": "Q4 founders",
            "channel": "linkedin",
            "category": "unclear",
            "intent_source": None,
            "excerpt": None,
            "replied_at": "2026-07-19T09:00:00+00:00",
            "communication_id": None,
            "inbox_thread_id": None,
            "touches": 1,
        },
    ],
    "items_total": 3,
    "truncated": True,
    "auto_replies": [
        {
            "recipient_id": "r5",
            "person_id": "p5",
            "person_name": "Cy Moss",
            "company_id": None,
            "company_name": None,
            "sequence_id": "s1",
            "sequence_name": "Q4 founders",
            "channel": "email",
            "category": "out_of_office",
            "intent_source": "rule",
            "excerpt": "I am away until Monday.",
            "replied_at": "2026-07-21T09:00:00+00:00",
            "communication_id": "m5",
            "inbox_thread_id": "t5",
            "touches": 1,
        }
    ],
    "auto_reply_count": 1,
    "bounced": [
        {
            "recipient_id": "r6",
            "person_id": "p6",
            "person_name": "Di Park",
            "company_id": None,
            "company_name": None,
            "sequence_id": "s1",
            "sequence_name": "Q4 founders",
            "email": "di@example.com",
            "bounced_at": "2026-07-18T10:00:00+00:00",
            "emails": 2,
            "communication_id": "m6",
        }
    ],
    "bounced_count": 1,
    "bounced_emails": 2,
}


def test_analytics_replies(invoke, mock_api):
    route = mock_api.get("/api/v1/analytics/replies").respond(200, json=REPLIES)
    result = invoke(["analytics", "replies"])
    assert result.exit_code == 0, result.output
    assert dict(route.calls.last.request.url.params) == {"period_days": "30"}
    assert "Replies: 3" in result.output
    assert "Interested" in result.output
    assert "Out of office" in result.output
    assert "Ann Lee" in result.output
    assert "Acme [beta]" in result.output
    # The table can wrap the excerpt.
    assert "Yes, send" in result.output
    assert "LinkedIn" in result.output
    assert "Showing 2 of 3" in result.output
    assert "Automatic replies: 1 (not counted in Replies)" in result.output
    assert "Cy Moss" in result.output
    assert "Bounced: 1 prospects, 2 emails (not counted in Replies)" in result.output
    assert "di@example.com" in result.output


def test_analytics_replies_sends_every_option(invoke, mock_api):
    touches = {
        **REPLIES,
        "scope": "touches",
        "channel": "linkedin",
        "category": "no_response",
        "by_category": {**_CATEGORIES, "no_response": 4},
        "touches_by_category": {**_CATEGORIES, "no_response": 9},
    }
    route = mock_api.get("/api/v1/analytics/replies").respond(200, json=touches)
    result = invoke(
        [
            "analytics",
            "replies",
            "--period-days",
            "7",
            "--scope",
            "touches",
            "--channel",
            "linkedin",
            "--category",
            "no_response",
            "--limit",
            "20",
        ]
    )
    assert result.exit_code == 0, result.output
    assert dict(route.calls.last.request.url.params) == {
        "period_days": "7",
        "scope": "touches",
        "channel": "linkedin",
        "category": "no_response",
        "limit": "20",
    }
    assert "Prospects touched: 3" in result.output
    assert "No response" in result.output


def test_analytics_replies_json(invoke, mock_api):
    mock_api.get("/api/v1/analytics/replies").respond(200, json=REPLIES)
    result = invoke(["analytics", "replies", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output) == REPLIES


def test_analytics_replies_with_no_replies(invoke, mock_api):
    empty = {
        **REPLIES,
        "total": 0,
        "by_category": dict.fromkeys(_CATEGORIES, 0),
        "items": [],
        "items_total": 0,
        "truncated": False,
        "auto_replies": [],
        "auto_reply_count": 0,
        "bounced": [],
        "bounced_count": 0,
        "bounced_emails": 0,
    }
    mock_api.get("/api/v1/analytics/replies").respond(200, json=empty)
    result = invoke(["analytics", "replies"])
    assert result.exit_code == 0
    assert "Replies: 0" in result.output
    assert "No replies in this period" in result.output
    assert "Automatic replies: 0 (not counted in Replies)" in result.output


def test_analytics_replies_touches_needs_a_channel_before_request(invoke, mock_api):
    result = invoke(["analytics", "replies", "--scope", "touches", "--json"])
    assert result.exit_code == 2
    assert json.loads(result.output)["error"] is True
    assert not mock_api.calls


@pytest.mark.parametrize(
    "args",
    [
        ["--scope", "people"],
        ["--channel", "whatsapp"],
        ["--category", "positive"],
        ["--limit", "501"],
        ["--period-days", "0"],
    ],
)
def test_analytics_replies_refuses_a_bad_option_before_request(invoke, mock_api, args):
    result = invoke(["analytics", "replies", *args, "--json"])
    assert result.exit_code == 2
    assert json.loads(result.output)["error"] is True
    assert not mock_api.calls


def test_analytics_replies_error_json(invoke, mock_api):
    mock_api.get("/api/v1/analytics/replies").respond(400, json={"detail": "bad"})
    result = invoke(["analytics", "replies", "--json"])
    assert result.exit_code == 1
    body = json.loads(result.output)
    assert body["status_code"] == 400
    assert body["detail"] == "bad"

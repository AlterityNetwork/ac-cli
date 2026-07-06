"""Tests for admin billing commands."""

import json

SAMPLE_STRIPE_SUBS = {
    "data": [
        {
            "id": "sub_live_1",
            "customer_id": "cus_1",
            "status": "active",
            "product_id": "prod_1",
            "amount": 5000,
            "currency": "gbp",
            "linked_local_subscription_id": "loc-1",
            "is_orphan": False,
        },
        {
            "id": "sub_live_2",
            "customer_id": "cus_2",
            "status": "canceled",
            "product_id": "prod_1",
            "amount": 5000,
            "currency": "gbp",
            "linked_local_subscription_id": None,
            "is_orphan": True,
        },
    ],
    "broken_links": [
        {
            "local_subscription_id": "loc-9",
            "organization_id": "org-9",
            "stripe_subscription_id": "sub_gone",
        }
    ],
    "total": 2,
}


def test_stripe_subscriptions_list(invoke, mock_api):
    mock_api.get("/api/v1/admin/billing/stripe-subscriptions").respond(200, json=SAMPLE_STRIPE_SUBS)
    result = invoke(["admin", "billing", "stripe-subscriptions"])
    assert result.exit_code == 0
    assert "sub_live_1" in result.output
    # The broken-links table is surfaced too.
    assert "sub_gone" in result.output


def test_stripe_subscriptions_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/billing/stripe-subscriptions").respond(200, json=SAMPLE_STRIPE_SUBS)
    result = invoke(["admin", "billing", "stripe-subscriptions", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["total"] == 2
    assert len(data["broken_links"]) == 1

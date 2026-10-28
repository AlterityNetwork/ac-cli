"""Tests for the admin agency matching commands."""

import json

import httpx

ORG = "00000000-0000-0000-0000-00000000000a"
OTHER = "00000000-0000-0000-0000-00000000000b"

COVERAGE = {
    "has_description": True,
    "has_services": True,
    "crm_companies": 300,
    "crm_engaged": 2,
    "crm_deals": 0,
    "saved_searches": 4,
    "search_runs": 10,
    "legacy_search_runs": 50,
    "offers": 1,
    "memories": 0,
    "referrals_made": 0,
}

SUMMARY = {
    "organization_id": ORG,
    "name": "Alpha Agency",
    "home_country": "GB",
    "website_url": "https://alpha.example",
    "is_demo": False,
    "onboarding_status": "active",
    "service_tags": [{"tag": "seo", "label": "SEO"}],
    "top_industries": [{"value": "Retail", "share": 0.6}],
    "top_countries": [{"value": "GB", "share": 1.0}],
    "coverage": COVERAGE,
    "top_complementary": {"organization_id": OTHER, "name": "Beta Studio", "score": 0.71},
    "top_similar": {"organization_id": OTHER, "name": "Gamma Works", "score": 0.52},
}

MATCH = {
    "organization_id": OTHER,
    "name": "Beta Studio",
    "is_demo": False,
    "score": 0.71,
    "complementary_score": 0.71,
    "similar_score": 0.4,
    "competitor": False,
    "factors": {
        "market": 0.8,
        "geography": 1.0,
        "service_overlap": 0.0,
        "complementarity": 1.0,
        "shared_accounts": 0.1,
        "shared_account_count": 3,
        "engaged_shared_account_count": 0,
    },
    "reasons": ["Both target Retail."],
    "service_tags": [{"tag": "brand", "label": "Brand"}],
}

WEIGHTS = {"market": 0.4, "geography": 0.2, "services": 0.3, "accounts": 0.1}


def test_agencies_lists_summaries(invoke, mock_api):
    route = mock_api.get("/api/v1/admin/agency-matching/agencies").respond(
        200,
        json={"data": [SUMMARY], "total": 1, "source": "database"},
    )
    result = invoke(["admin", "matching", "agencies"])
    assert result.exit_code == 0
    assert "Alpha Agency" in result.output
    assert "Beta Studio" in result.output
    assert "Gamma Works" in result.output
    url = str(route.calls.last.request.url)
    assert "include_demo=false" in url
    assert "lens" not in url


def test_agencies_passes_the_demo_flag(invoke, mock_api):
    route = mock_api.get("/api/v1/admin/agency-matching/agencies").respond(
        200, json={"data": [], "total": 0, "source": "database"}
    )
    result = invoke(["admin", "matching", "agencies", "--include-demo", "--json"])
    assert result.exit_code == 0
    assert "include_demo=true" in str(route.calls.last.request.url)
    assert json.loads(result.output)["total"] == 0


def test_agency_shows_ranked_matches(invoke, mock_api):
    route = mock_api.get(f"/api/v1/admin/agency-matching/agencies/{ORG}").respond(
        200,
        json={
            "agency": SUMMARY,
            "description": "An agency.",
            "service_lines": ["SEO"],
            "industries": [],
            "countries": [],
            "sizes": [],
            "lens": "complementary",
            "weights": WEIGHTS,
            "matches": [MATCH],
            "source": "database",
        },
    )
    result = invoke(["admin", "matching", "agency", ORG, "--w-market", "1", "--w-accounts", "0"])
    assert result.exit_code == 0
    assert "Beta Studio" in result.output
    url = str(route.calls.last.request.url)
    assert "w_market=1" in url
    assert "w_accounts=0" in url
    assert "w_services" not in url


def test_agency_not_found(invoke, mock_api):
    mock_api.get(f"/api/v1/admin/agency-matching/agencies/{ORG}").respond(
        404, json={"detail": "No agency"}
    )
    result = invoke(["admin", "matching", "agency", ORG])
    assert result.exit_code == 3


def test_pair_shows_the_breakdown(invoke, mock_api):
    mock_api.get(f"/api/v1/admin/agency-matching/pairs/{ORG}/{OTHER}").respond(
        200,
        json={
            "agency_a": SUMMARY,
            "agency_b": {**SUMMARY, "organization_id": OTHER, "name": "Beta Studio"},
            "lens": "complementary",
            "weights": WEIGHTS,
            "match": MATCH,
            "shared_industries": [{"value": "Retail", "a_share": 0.6, "b_share": 0.5}],
            "shared_countries": [],
            "services_only_a": [{"tag": "seo", "label": "SEO"}],
            "services_only_b": [{"tag": "brand", "label": "Brand"}],
            "services_both": [],
            "shared_domains": [
                {"domain": "shop.example", "a_stage": "identified", "b_stage": "customer"}
            ],
            "shared_domain_total": 1,
            "source": "database",
        },
    )
    result = invoke(["admin", "matching", "pair", ORG, OTHER])
    assert result.exit_code == 0
    assert "Retail" in result.output
    assert "shop.example" in result.output


def test_pair_json(invoke, mock_api):
    payload = {"match": MATCH}
    mock_api.get(f"/api/v1/admin/agency-matching/pairs/{ORG}/{OTHER}").respond(200, json=payload)
    result = invoke(["admin", "matching", "pair", ORG, OTHER, "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["match"]["name"] == "Beta Studio"


PAIR_POINT = {
    "agency_a_id": ORG,
    "agency_a_name": "Alpha Agency",
    "agency_b_id": OTHER,
    "agency_b_name": "Beta Studio",
    "complementary_score": 0.71,
    "similar_score": 0.4,
    "competitor": True,
    "shared_account_count": 3,
}


def test_pairs_lists_every_pair_best_first(invoke, mock_api):
    route = mock_api.get("/api/v1/admin/agency-matching/pairs").respond(
        200,
        json={
            "data": [
                {**PAIR_POINT, "agency_b_name": "Low Pair", "complementary_score": 0.2},
                PAIR_POINT,
            ],
            "weights": WEIGHTS,
            "source": "database",
        },
    )
    result = invoke(["admin", "matching", "pairs", "--w-services", "0.5"])
    assert result.exit_code == 0
    assert result.output.index("Beta Studio") < result.output.index("Low Pair")
    assert "w_services=0.5" in str(route.calls.last.request.url)


def test_pairs_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/agency-matching/pairs").respond(
        200, json={"data": [PAIR_POINT], "weights": WEIGHTS, "source": "database"}
    )
    result = invoke(["admin", "matching", "pairs", "--include-demo", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["data"][0]["competitor"] is True


SCAN = {
    "organization_id": ORG,
    "name": "Alpha Agency",
    "website_url": "https://alpha.example",
    "status": "scanned",
    "description": "We grow brands.",
    "services": ["SEO", "Brand"],
    "industry": "Marketing",
    "logo_url": None,
}


import pytest  # noqa: E402

from ac_cli.commands.admin import agency_matching as agency_matching_module  # noqa: E402


@pytest.fixture(autouse=True)
def no_poll_wait(monkeypatch):
    monkeypatch.setattr(agency_matching_module, "POLL_SECONDS", 0)


def test_scan_website_starts_then_waits_for_the_result(invoke, mock_api):
    start = mock_api.post(f"/api/v1/admin/agency-matching/agencies/{ORG}/website-scan").respond(
        202, json={**SCAN, "status": "pending", "services": []}
    )
    status = mock_api.get(f"/api/v1/admin/agency-matching/agencies/{ORG}/website-scan")
    status.side_effect = [
        httpx.Response(200, json={**SCAN, "status": "pending", "services": []}),
        httpx.Response(200, json=SCAN),
    ]
    result = invoke(["admin", "matching", "scan-website", ORG])
    assert result.exit_code == 0
    assert start.called
    assert status.call_count == 2
    assert "scanned" in result.output
    assert "SEO" in result.output


def test_scan_status_reads_one_agency(invoke, mock_api):
    mock_api.get(f"/api/v1/admin/agency-matching/agencies/{ORG}/website-scan").respond(
        200, json=SCAN
    )
    result = invoke(["admin", "matching", "scan-status", ORG, "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["status"] == "scanned"


def test_scan_websites_starts_each_scan_then_waits(invoke, mock_api):
    mock_api.get("/api/v1/admin/agency-matching/agencies").respond(
        200,
        json={
            "data": [SUMMARY, {**SUMMARY, "organization_id": OTHER, "name": "Beta Studio"}],
            "total": 2,
            "source": "database",
        },
    )
    for org_id, final in ((ORG, "scanned"), (OTHER, "empty")):
        mock_api.post(f"/api/v1/admin/agency-matching/agencies/{org_id}/website-scan").respond(
            202, json={**SCAN, "organization_id": org_id, "status": "pending"}
        )
        mock_api.get(f"/api/v1/admin/agency-matching/agencies/{org_id}/website-scan").respond(
            200, json={**SCAN, "organization_id": org_id, "status": final}
        )
    result = invoke(["admin", "matching", "scan-websites", "--json"])
    assert result.exit_code == 0
    assert [r["status"] for r in json.loads(result.output)] == ["scanned", "empty"]


def test_weight_flags_include_client_size(invoke, mock_api):
    route = mock_api.get("/api/v1/admin/agency-matching/pairs").respond(
        200, json={"data": [], "weights": WEIGHTS, "source": "database"}
    )
    result = invoke(["admin", "matching", "pairs", "--w-size", "0.5", "--json"])
    assert result.exit_code == 0
    assert "w_size=0.5" in str(route.calls.last.request.url)


ALGORITHM = {
    "factors": [
        {
            "key": "market",
            "label": "Same industries",
            "description": "How alike the target industries are.",
            "sources": ["CRM company industries"],
            "complementary": "Same industries",
            "similar": "Same industries",
        }
    ],
    "default_weights": {**WEIGHTS, "size": 0.15},
    "competitor_threshold": 0.5,
    "size_tiers": [{"key": "startup", "label": "Under 50 staff"}],
    "service_tags": [{"tag": "seo", "label": "SEO"}],
    "excluded": ["Corbel's own organisations."],
}


def test_algorithm_shows_the_factors_and_weights(invoke, mock_api):
    mock_api.get("/api/v1/admin/agency-matching/algorithm").respond(200, json=ALGORITHM)
    result = invoke(["admin", "matching", "algorithm"])
    assert result.exit_code == 0
    assert "Same industries" in result.output
    assert "Under 50 staff" in result.output


def test_algorithm_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/agency-matching/algorithm").respond(200, json=ALGORITHM)
    result = invoke(["admin", "matching", "algorithm", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["competitor_threshold"] == 0.5


def test_agencies_passes_weights(invoke, mock_api):
    route = mock_api.get("/api/v1/admin/agency-matching/agencies").respond(
        200, json={"data": [], "total": 0, "source": "database"}
    )
    result = invoke(["admin", "matching", "agencies", "--w-size", "1", "--json"])
    assert result.exit_code == 0
    assert "w_size=1" in str(route.calls.last.request.url)


def test_every_weighted_command_passes_the_search_weight(invoke, mock_api):
    org = "00000000-0000-0000-0000-00000000000a"
    other = "00000000-0000-0000-0000-00000000000b"
    base = "/api/v1/admin/agency-matching"
    routes = {
        "agencies": mock_api.get(f"{base}/agencies").respond(
            200, json={"data": [], "total": 0, "source": "database"}
        ),
        "pairs": mock_api.get(f"{base}/pairs").respond(
            200, json={"data": [], "source": "database"}
        ),
        "agency": mock_api.get(f"{base}/agencies/{org}").respond(200, json={}),
        "pair": mock_api.get(f"{base}/pairs/{org}/{other}").respond(200, json={}),
    }
    commands = {
        "agencies": ["agencies"],
        "pairs": ["pairs"],
        "agency": ["agency", org],
        "pair": ["pair", org, other],
    }

    for name, args in commands.items():
        result = invoke(["admin", "matching", *args, "--w-searches", "0.4", "--json"])
        assert result.exit_code == 0, name
        assert "w_searches=0.4" in str(routes[name].calls.last.request.url), name

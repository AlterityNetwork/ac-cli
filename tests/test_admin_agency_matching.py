"""Tests for the admin agency matching commands."""

import json

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
    "top_match": {"organization_id": OTHER, "name": "Beta Studio", "score": 0.71},
}

MATCH = {
    "organization_id": OTHER,
    "name": "Beta Studio",
    "is_demo": False,
    "score": 0.71,
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
        json={"data": [SUMMARY], "total": 1, "lens": "complementary", "source": "database"},
    )
    result = invoke(["admin", "matching", "agencies"])
    assert result.exit_code == 0
    assert "Alpha Agency" in result.output
    assert "Beta Studio" in result.output
    url = str(route.calls.last.request.url)
    assert "include_demo=false" in url
    assert "lens=complementary" in url


def test_agencies_passes_demo_and_lens(invoke, mock_api):
    route = mock_api.get("/api/v1/admin/agency-matching/agencies").respond(
        200, json={"data": [], "total": 0, "lens": "similar", "source": "database"}
    )
    result = invoke(
        ["admin", "matching", "agencies", "--include-demo", "--lens", "similar", "--json"]
    )
    assert result.exit_code == 0
    url = str(route.calls.last.request.url)
    assert "include_demo=true" in url
    assert "lens=similar" in url
    assert json.loads(result.output)["lens"] == "similar"


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

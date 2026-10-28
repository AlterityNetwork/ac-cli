"""Admin agency matching commands (super admin only, read-only)."""

from __future__ import annotations

import time

import typer
from rich import print as rprint

from ac_cli.commands._helpers import JSON_OPTION, _api_request, set_json_mode
from ac_cli.commands.admin import _ADMIN
from ac_cli.formatting import print_json, print_table, styled

agency_matching_app = typer.Typer(help="Agency matching: profiles and ranked matches")

# A website scan runs on the server after the request that starts it.
POLL_SECONDS = 3
POLL_LIMIT_SECONDS = 180

LENS_OPTION = typer.Option(
    "complementary",
    "--lens",
    help="complementary (joint pitch, referral) or similar (overflow work)",
)


def _weight_params(
    market: float | None,
    geography: float | None,
    services: float | None,
    accounts: float | None,
    size: float | None = None,
    searches: float | None = None,
) -> dict:
    """Returns the weight query params that the user set."""
    params: dict = {}
    for key, value in (
        ("w_market", market),
        ("w_geography", geography),
        ("w_services", services),
        ("w_accounts", accounts),
        ("w_size", size),
        ("w_searches", searches),
    ):
        if value is not None:
            params[key] = value
    return params


def _tags(tags: list[dict] | None) -> str:
    if tags is None:
        return "untagged"
    return ", ".join(t.get("label", t.get("tag", "")) for t in tags)


def _pct(value: float | None) -> str:
    return "-" if value is None else f"{value * 100:.0f}%"


def _best(match: dict | None) -> str:
    if not match:
        return "-"
    return f"{match.get('name')} {_pct(match.get('score'))}"


@agency_matching_app.command("agencies")
def agencies(
    ctx: typer.Context,
    include_demo: bool = typer.Option(False, "--include-demo", help="Include demo organisations"),
    w_market: float | None = typer.Option(
        None, "--w-market", help="Weight of market overlap (0-1)"
    ),
    w_geography: float | None = typer.Option(
        None, "--w-geography", help="Weight of geography (0-1)"
    ),
    w_services: float | None = typer.Option(
        None, "--w-services", help="Weight of the service factor (0-1)"
    ),
    w_accounts: float | None = typer.Option(
        None, "--w-accounts", help="Weight of shared accounts (0-1)"
    ),
    w_size: float | None = typer.Option(
        None, "--w-size", help="Weight of the client size factor (0-1)"
    ),
    w_searches: float | None = typer.Option(
        None, "--w-searches", help="Weight of the search target factor (0-1)"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """List agencies with their best complementary and best similar match."""
    set_json_mode(json_output)
    resp = _api_request(
        "get",
        f"{_ADMIN}/agency-matching/agencies",
        params={
            "include_demo": str(include_demo).lower(),
            **_weight_params(w_market, w_geography, w_services, w_accounts, w_size, w_searches),
        },
    )
    data = resp.json()
    if json_output:
        print_json(data)
        return
    rows = [
        {
            "name": agency.get("name"),
            "services": _tags(agency.get("service_tags")),
            "complementary": _best(agency.get("top_complementary")),
            "similar": _best(agency.get("top_similar")),
            "id": agency.get("organization_id"),
        }
        for agency in data.get("data", [])
    ]
    print_table(
        rows,
        [
            ("name", "Agency"),
            ("services", "Services"),
            ("complementary", "Best complementary"),
            ("similar", "Best similar"),
            ("id", "ID"),
        ],
        title=f"Agencies ({data.get('total', '?')}, source {data.get('source')})",
    )


@agency_matching_app.command("pairs")
def pairs(
    ctx: typer.Context,
    include_demo: bool = typer.Option(False, "--include-demo", help="Include demo organisations"),
    w_market: float | None = typer.Option(
        None, "--w-market", help="Weight of market overlap (0-1)"
    ),
    w_geography: float | None = typer.Option(
        None, "--w-geography", help="Weight of geography (0-1)"
    ),
    w_services: float | None = typer.Option(
        None, "--w-services", help="Weight of the service factor (0-1)"
    ),
    w_accounts: float | None = typer.Option(
        None, "--w-accounts", help="Weight of shared accounts (0-1)"
    ),
    w_size: float | None = typer.Option(
        None, "--w-size", help="Weight of the client size factor (0-1)"
    ),
    w_searches: float | None = typer.Option(
        None, "--w-searches", help="Weight of the search target factor (0-1)"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """List every pair of agencies with both scores, best complementary first."""
    set_json_mode(json_output)
    params: dict = {"include_demo": str(include_demo).lower()}
    params.update(_weight_params(w_market, w_geography, w_services, w_accounts, w_size, w_searches))
    resp = _api_request("get", f"{_ADMIN}/agency-matching/pairs", params=params)
    data = resp.json()
    if json_output:
        print_json(data)
        return
    points = sorted(data.get("data", []), key=lambda p: -p.get("complementary_score", 0))
    rows = [
        {
            "pair": f"{p.get('agency_a_name')} and {p.get('agency_b_name')}"
            + (" (competitor)" if p.get("competitor") else ""),
            "complementary": _pct(p.get("complementary_score")),
            "similar": _pct(p.get("similar_score")),
            "shared": p.get("shared_account_count", 0),
        }
        for p in points
    ]
    print_table(
        rows,
        [
            ("pair", "Pair"),
            ("complementary", "Complementary"),
            ("similar", "Similar"),
            ("shared", "Shared CRM"),
        ],
        title=f"Pairs ({len(rows)}, source {data.get('source')})",
    )


@agency_matching_app.command("agency")
def agency(
    ctx: typer.Context,
    org_id: str = typer.Argument(..., help="Organisation ID"),
    include_demo: bool = typer.Option(False, "--include-demo", help="Include demo organisations"),
    lens: str = LENS_OPTION,
    w_market: float | None = typer.Option(
        None, "--w-market", help="Weight of market overlap (0-1)"
    ),
    w_geography: float | None = typer.Option(
        None, "--w-geography", help="Weight of geography (0-1)"
    ),
    w_services: float | None = typer.Option(
        None, "--w-services", help="Weight of the service factor (0-1)"
    ),
    w_accounts: float | None = typer.Option(
        None, "--w-accounts", help="Weight of shared accounts (0-1)"
    ),
    w_size: float | None = typer.Option(
        None, "--w-size", help="Weight of the client size factor (0-1)"
    ),
    w_searches: float | None = typer.Option(
        None, "--w-searches", help="Weight of the search target factor (0-1)"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Show one agency profile and its ranked matches."""
    set_json_mode(json_output)
    params = {"include_demo": str(include_demo).lower(), "lens": lens}
    params.update(_weight_params(w_market, w_geography, w_services, w_accounts, w_size, w_searches))
    resp = _api_request("get", f"{_ADMIN}/agency-matching/agencies/{org_id}", params=params)
    data = resp.json()
    if json_output:
        print_json(data)
        return
    summary = data.get("agency", {})
    rprint(
        styled(
            "[bold]{}[/bold]  services: {}", summary.get("name"), _tags(summary.get("service_tags"))
        )
    )
    rows = []
    for match in data.get("matches", []):
        factors = match.get("factors", {})
        rows.append(
            {
                "name": f"{match.get('name')} (competitor)"
                if match.get("competitor")
                else match.get("name"),
                "complementary": _pct(match.get("complementary_score")),
                "similar": _pct(match.get("similar_score")),
                "overlap": _pct(factors.get("service_overlap")),
                "searches": _pct(factors.get("search_overlap")),
                "id": match.get("organization_id"),
            }
        )
    print_table(
        rows,
        [
            ("name", "Match"),
            ("complementary", "Complementary"),
            ("similar", "Similar"),
            ("overlap", "Service overlap"),
            ("searches", "Search targets"),
            ("id", "ID"),
        ],
        title=f"Matches (sorted by {data.get('lens')}, source {data.get('source')})",
    )


@agency_matching_app.command("pair")
def pair(
    ctx: typer.Context,
    org_a: str = typer.Argument(..., help="First organisation ID"),
    org_b: str = typer.Argument(..., help="Second organisation ID"),
    lens: str = LENS_OPTION,
    w_market: float | None = typer.Option(
        None, "--w-market", help="Weight of market overlap (0-1)"
    ),
    w_geography: float | None = typer.Option(
        None, "--w-geography", help="Weight of geography (0-1)"
    ),
    w_services: float | None = typer.Option(
        None, "--w-services", help="Weight of the service factor (0-1)"
    ),
    w_accounts: float | None = typer.Option(
        None, "--w-accounts", help="Weight of shared accounts (0-1)"
    ),
    w_size: float | None = typer.Option(
        None, "--w-size", help="Weight of the client size factor (0-1)"
    ),
    w_searches: float | None = typer.Option(
        None, "--w-searches", help="Weight of the search target factor (0-1)"
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Show the factor breakdown of one pair of agencies."""
    set_json_mode(json_output)
    params = {"lens": lens}
    params.update(_weight_params(w_market, w_geography, w_services, w_accounts, w_size, w_searches))
    resp = _api_request("get", f"{_ADMIN}/agency-matching/pairs/{org_a}/{org_b}", params=params)
    data = resp.json()
    if json_output:
        print_json(data)
        return
    match = data.get("match", {})
    a = data.get("agency_a", {}).get("name")
    b = data.get("agency_b", {}).get("name")
    rprint(styled("[bold]{} and {}[/bold]  score {}", a, b, _pct(match.get("score"))))
    for reason in match.get("reasons", []):
        rprint(styled("  - {}", reason))
    print_table(
        [
            {"value": v["value"], "a": _pct(v.get("a_share")), "b": _pct(v.get("b_share"))}
            for v in data.get("shared_industries", [])
        ],
        [("value", "Shared industry"), ("a", a or "A"), ("b", b or "B")],
    )
    print_table(
        data.get("shared_domains", []),
        [("domain", "Shared CRM domain"), ("a_stage", a or "A"), ("b_stage", b or "B")],
        title=f"Shared CRM companies ({data.get('shared_domain_total', 0)} total)",
    )


def _wait_for_scan(org_id: str) -> dict:
    """Reads the scan status until the scan is no longer pending."""
    deadline = time.monotonic() + POLL_LIMIT_SECONDS
    while True:
        data = _api_request(
            "get", f"{_ADMIN}/agency-matching/agencies/{org_id}/website-scan"
        ).json()
        if data.get("status") != "pending" or time.monotonic() >= deadline:
            return data
        time.sleep(POLL_SECONDS)


def _print_scan(data: dict) -> None:
    rprint(
        styled(
            "[bold]{}[/bold]  {}  {}", data.get("name"), data.get("website_url"), data.get("status")
        )
    )
    if data.get("services"):
        rprint(styled("  services: {}", ", ".join(data["services"])))
    if data.get("description"):
        rprint(styled("  {}", data["description"]))


@agency_matching_app.command("scan-website")
def scan_website(
    ctx: typer.Context,
    org_id: str = typer.Argument(..., help="Organisation ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Scan the homepage of one agency and wait for the result (kept 30 days)."""
    set_json_mode(json_output)
    _api_request("post", f"{_ADMIN}/agency-matching/agencies/{org_id}/website-scan")
    data = _wait_for_scan(org_id)
    if json_output:
        print_json(data)
        return
    _print_scan(data)


@agency_matching_app.command("scan-status")
def scan_status(
    ctx: typer.Context,
    org_id: str = typer.Argument(..., help="Organisation ID"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Show the status and the result of the website scan of one agency."""
    set_json_mode(json_output)
    data = _api_request("get", f"{_ADMIN}/agency-matching/agencies/{org_id}/website-scan").json()
    if json_output:
        print_json(data)
        return
    _print_scan(data)


@agency_matching_app.command("scan-websites")
def scan_websites(
    ctx: typer.Context,
    include_demo: bool = typer.Option(False, "--include-demo", help="Include demo organisations"),
    json_output: bool = JSON_OPTION,
) -> None:
    """Scan the homepage of every listed agency, then wait for every result."""
    set_json_mode(json_output)
    listing = _api_request(
        "get",
        f"{_ADMIN}/agency-matching/agencies",
        params={"include_demo": str(include_demo).lower()},
    ).json()
    org_ids = [a["organization_id"] for a in listing.get("data", []) if a.get("website_url")]
    for org_id in org_ids:
        _api_request("post", f"{_ADMIN}/agency-matching/agencies/{org_id}/website-scan")
    results = [_wait_for_scan(org_id) for org_id in org_ids]
    if json_output:
        print_json(results)
        return
    print_table(
        [
            {"name": r.get("name"), "status": r.get("status"), "website": r.get("website_url")}
            for r in results
        ],
        [("name", "Agency"), ("status", "Scan"), ("website", "Website")],
        title=f"Website scans ({len(results)})",
    )


@agency_matching_app.command("algorithm")
def algorithm(ctx: typer.Context, json_output: bool = JSON_OPTION) -> None:
    """Show the factors, the default weights and the fixed parameters of matching."""
    set_json_mode(json_output)
    data = _api_request("get", f"{_ADMIN}/agency-matching/algorithm").json()
    if json_output:
        print_json(data)
        return
    weights = data.get("default_weights", {})
    print_table(
        [
            {
                "factor": f.get("label"),
                "weight": weights.get(f.get("key")),
                "complementary": f.get("complementary"),
                "similar": f.get("similar"),
            }
            for f in data.get("factors", [])
        ],
        [
            ("factor", "Factor"),
            ("weight", "Default weight"),
            ("complementary", "Complementary"),
            ("similar", "Similar"),
        ],
        title="Agency matching factors",
    )
    rprint(
        styled(
            "Competitor: service and market overlap both at least {}",
            data.get("competitor_threshold"),
        )
    )
    rprint(styled("Client sizes: {}", ", ".join(t["label"] for t in data.get("size_tiers", []))))
    for line in data.get("excluded", []):
        rprint(styled("Left out: {}", line))

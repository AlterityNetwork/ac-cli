"""Admin agency matching commands (super admin only, read-only)."""

from __future__ import annotations

import typer
from rich import print as rprint

from ac_cli.commands._helpers import JSON_OPTION, _api_request, set_json_mode
from ac_cli.commands.admin import _ADMIN
from ac_cli.formatting import print_json, print_table, styled

agency_matching_app = typer.Typer(help="Agency matching: profiles and ranked matches")

LENS_OPTION = typer.Option(
    "complementary",
    "--lens",
    help="complementary (joint pitch, referral) or similar (overflow work)",
)


def _weight_params(
    market: float | None, geography: float | None, services: float | None, accounts: float | None
) -> dict:
    """Returns the weight query params that the user set."""
    params: dict = {}
    for key, value in (
        ("w_market", market),
        ("w_geography", geography),
        ("w_services", services),
        ("w_accounts", accounts),
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


@agency_matching_app.command("agencies")
def agencies(
    ctx: typer.Context,
    include_demo: bool = typer.Option(False, "--include-demo", help="Include demo organisations"),
    lens: str = LENS_OPTION,
    json_output: bool = JSON_OPTION,
) -> None:
    """List agencies with their data coverage and their best match."""
    set_json_mode(json_output)
    resp = _api_request(
        "get",
        f"{_ADMIN}/agency-matching/agencies",
        params={"include_demo": str(include_demo).lower(), "lens": lens},
    )
    data = resp.json()
    if json_output:
        print_json(data)
        return
    rows = []
    for agency in data.get("data", []):
        top = agency.get("top_match") or {}
        rows.append(
            {
                "name": agency.get("name"),
                "services": _tags(agency.get("service_tags")),
                "top_match": top.get("name", "-"),
                "score": _pct(top.get("score")),
                "id": agency.get("organization_id"),
            }
        )
    print_table(
        rows,
        [
            ("name", "Agency"),
            ("services", "Services"),
            ("top_match", "Top match"),
            ("score", "Score"),
            ("id", "ID"),
        ],
        title=f"Agencies ({data.get('total', '?')}, lens {data.get('lens')}, source {data.get('source')})",
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
    json_output: bool = JSON_OPTION,
) -> None:
    """Show one agency profile and its ranked matches."""
    set_json_mode(json_output)
    params = {"include_demo": str(include_demo).lower(), "lens": lens}
    params.update(_weight_params(w_market, w_geography, w_services, w_accounts))
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
                "score": _pct(match.get("score")),
                "market": _pct(factors.get("market")),
                "services": _pct(
                    factors.get("complementarity")
                    if lens == "complementary"
                    else factors.get("service_overlap")
                ),
                "id": match.get("organization_id"),
            }
        )
    print_table(
        rows,
        [
            ("name", "Match"),
            ("score", "Score"),
            ("market", "Market"),
            ("services", "Services"),
            ("id", "ID"),
        ],
        title=f"Matches (lens {data.get('lens')}, source {data.get('source')})",
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
    json_output: bool = JSON_OPTION,
) -> None:
    """Show the factor breakdown of one pair of agencies."""
    set_json_mode(json_output)
    params = {"lens": lens}
    params.update(_weight_params(w_market, w_geography, w_services, w_accounts))
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

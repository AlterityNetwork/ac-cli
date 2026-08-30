#!/usr/bin/env python3
"""Audit ac-cli HTTP calls against the FastAPI router surface.

Source-of-truth for API endpoints: ``/openapi.json`` from a running API
(``--api-url`` or ``AC_AUDIT_API_URL`` — defaults to localhost:8008). The
OpenAPI spec is the only fully accurate enumeration since routers are
mounted at runtime via lazy imports in ``ac-python-api/src/api/main.py``.

Source-of-truth for CLI calls: regex over ``_api_request(...)`` calls in
``src/ac_cli/commands/``, with ``PATH_CONSTANTS`` substitution.

Emits three lists:
  CLI-ONLY: paths the CLI calls that no API endpoint exposes (likely stale).
  API-ONLY: endpoints the API exposes that the CLI never calls (gap).
  METHOD-DIFF: same path on both sides, different HTTP methods.

``--strict`` exits nonzero on any CLI-ONLY finding (CI gate).
``OUT_OF_SCOPE`` lists API endpoints intentionally not exposed by CLI.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

CLI_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_API_URL = os.environ.get("AC_AUDIT_API_URL", "http://localhost:8008")

# Path constants used inside f-strings in the CLI command files.
PATH_CONSTANTS: dict[str, str] = {
    "_ADMIN": "/api/v1/admin",
    "_AGENTIC": "/api/v1/agentic",
    "_AGENTS": "/api/v1/agents",
    "_ANALYTICS": "/api/v1/analytics",
    "_APPS": "/api/v1/orgs",
    "_CHAT": "/api/v1/chat",
    "_CONVERSATIONS": "/api/v1/agentic/conversations",
    "_CRM": "/api/v1/crm",
    "_ENVOY": "/api/v1/envoy",
    "_FILES": "/api/v1/files",
    "_IMPERSONATION": "/api/v1/impersonation",
    "_INTEL": "/api/v1/admin/intelligence",
    "_LAUNCHPAD": "/api/v1/launchpad",
    "_LEGAL": "/api/v1/legal-documents",
    "_MERGE": "/api/v1/crm/companies/merge",
    "_MKT": "/api/v1/marketplace",
    "_NET": "/api/v1/network",
    "_NOTIFICATIONS": "/api/v1/notifications",
    "_NYLAS": "/api/v1/nylas",
    "_ONBOARDING": "/api/v1/admin/onboarding",
    "_ONBOARD": "/api/v1/managed-onboarding",
    "_PROFILES": "/api/v1/profiles",
    "_PROSPECTS": "/api/v1/agentic/prospects",
    "_SAVED_SEARCHES": "/api/v1/agentic/saved-searches",
    "_RESOURCES": "/api/v1/resources",
    "_STYLES": "/api/v1/writing-styles",
    "_TOS": "/api/v1/tos",
    "_WORKFLOWS": "/api/v1/workflows",
    "_BASE": "/api/v1/admin/searches",
    "_BATTLECARDS": "/api/v1/battlecards",
    "_PLAYBOOKS": "/api/v1/playbooks",
}

# API endpoints intentionally not covered by the CLI.
OUT_OF_SCOPE: set[tuple[str, str]] = {
    # Frontend-only UI state: CRM surfaces poll this for the per-company
    # "Headhunter search in progress" indicator; not a CLI workflow.
    ("GET", "/api/v1/workflows/headhunter/active-runs"),
    # Frontend-only widget composition: batches the Launchpad's per-saved-search
    # company windows into one request. `runs/companies?preset_id=` covers the
    # same data one preset at a time, which is the CLI-shaped call.
    ("GET", "/api/v1/workflows/{id}/runs/companies/by-preset"),
    # Signature-authenticated FullEnrich provider callbacks (ENG-1733).
    ("POST", "/api/v1/fullenrich/webhook"),
    ("POST", "/api/v1/fullenrich/webhook/contact"),
    # ENG-2048: public browser-only redemption of a managed-onboarding link.
    # The customer clicks a mailed URL with no session; the single-use token in
    # the body is the whole credential. Same class as the OAuth callback below.
    ("POST", "/api/v1/onboarding/redeem"),
    ("GET", "/api/v1/nylas/oauth/callback"),
    ("GET", "/api/v1/demo/nylas/account"),
    ("GET", "/api/v1/demo/nylas/messages/{id}/attachments/{id}/download"),
    ("POST", "/api/v1/demo/nylas/disconnect"),
    ("POST", "/api/v1/demo/nylas/send"),
    ("POST", "/api/v1/demo/nylas/threads/{id}/sync"),
    ("POST", "/api/v1/test/simulate-reply"),
    ("GET", "/api/v1/test/sent-emails"),
    ("DELETE", "/api/v1/test/sent-emails"),
    # ENG-783: e2e-only launchpad fixture seed/cleanup used by Playwright auth.setup.ts.
    ("POST", "/api/v1/test/seed-launchpad"),
    ("POST", "/api/v1/test/cleanup-launchpad"),
    # ENG-794: e2e-only notification trigger for two-context SSE Playwright spec.
    ("POST", "/api/v1/test/seed-notification"),
    # e2e-only headhunter fixture seed/cleanup used by Playwright runs.
    ("POST", "/api/v1/test/seed-headhunter"),
    ("POST", "/api/v1/test/cleanup-headhunter"),
    # ENG-1137: e2e/QA-only Sonar + Envoy installed-app fixture seed/cleanup.
    ("POST", "/api/v1/test/seed-sonar"),
    ("POST", "/api/v1/test/cleanup-sonar"),
    ("POST", "/api/v1/test/seed-envoy"),
    ("POST", "/api/v1/test/cleanup-envoy"),
    # ENG-1763: QA-only stale artifact cleanup for nightly staging runs.
    ("POST", "/api/v1/test/cleanup-qa-artifacts"),
    ("POST", "/api/v1/eval/run"),
    ("PATCH", "/api/v1/eval/runs/{id}"),
    ("DELETE", "/api/v1/eval/run/live/{id}"),
    ("PUT", "/api/v1/eval/fixtures/{id}"),
    ("POST", "/api/v1/admin/demo/scrape-website-stream"),
    ("POST", "/api/v1/admin/demo/generate-random-org-stream"),
    ("POST", "/api/v1/admin/demo/generate-random-profile-stream"),
    ("POST", "/api/v1/admin/demo/prepare-account-stream"),
    ("POST", "/api/v1/organizations/scrape-website-stream"),
    ("GET", "/api/v1/envoy/sequences/{id}/step-stats/stream"),
    ("GET", "/api/v1/workflows/{id}/runs/{id}/events"),
    # Managed agents SSE event stream — frontend/live-tail consumer only
    ("GET", "/api/v1/agents/runs/{id}/events"),
    # Frontend-only per-field invalidation stream (ENG-1733).
    ("GET", "/api/v1/workflows/{id}/runs/{id}/field-updates/stream"),
    # Frontend-only company lead_score invalidation stream (backgrounded judge).
    ("GET", "/api/v1/workflows/{id}/runs/{id}/companies/field-updates/stream"),
    # SSE stream — frontend-only consumer (ENG-769)
    ("GET", "/api/v1/notifications/stream"),
    # ENG-2124: the agentic run stream. SSE is not a CLI shape — the command
    # would never return, and the events are a live hint whose durable record
    # the CLI already reads through `runs get` and `runs spans`. Only this SSE
    # route is out of scope. ENG-2126 shipped `ac agentic runs spans --since`,
    # so the CLI does drive the reconnect; the filter is a query parameter,
    # which this audit does not compare.
    ("GET", "/api/v1/agentic/runs/{id}/stream"),
    ("GET", "/api/v1/resources/{id}/stream"),
    ("GET", "/api/v1/resources/{id}/preview-url"),
    ("PATCH", "/api/v1/resources/{id}"),
    ("GET", "/api/v1/nylas/sync/messages/{id}/attachments/{id}/download"),
    # battlecards/playbooks: non-envoy mounts duplicate routes — CLI uses /envoy/*
    ("GET", "/api/v1/battlecards/{id}"),
    ("PATCH", "/api/v1/battlecards/{id}"),
    ("DELETE", "/api/v1/battlecards/{id}"),
    ("POST", "/api/v1/battlecards/{id}/duplicate"),
    ("GET", "/api/v1/playbooks/{id}"),
    ("PATCH", "/api/v1/playbooks/{id}"),
    ("DELETE", "/api/v1/playbooks/{id}"),
    ("POST", "/api/v1/playbooks/{id}/duplicate"),
    ("POST", "/api/v1/orgs/{id}/apps/{id}/ensure-workflow"),
    # Non-versioned roots (CLI uses /health directly, not via API_V1)
    ("GET", "/"),
    ("GET", "/health"),
    # Nylas webhook + public unsubscribe link (not user-callable)
    ("GET", "/api/v1/nylas/webhook"),
    ("POST", "/api/v1/nylas/webhook"),
    ("GET", "/api/v1/nylas/email/unsubscribe"),
    ("POST", "/api/v1/nylas/email/unsubscribe"),
    # Resend bounce/complaint webhook (signature-verified server-to-server) [ENG-768]
    ("POST", "/api/v1/webhooks/resend"),
    # FullEnrich bulk-enrichment completion webhook (URL-token-authed, server-to-server)
    ("POST", "/api/v1/fullenrich/webhook"),
    # Anthropic agent-runtime session webhook (signature-verified server-to-server).
    # Route is /agent-runtime/{provider}/webhook; OUT_OF_SCOPE is matched raw against
    # normalized API paths, so the param must be the normalized {id} form.
    ("POST", "/api/v1/agent-runtime/{id}/webhook"),
    # Frontend-only activity logger
    ("POST", "/api/v1/orgs/{id}/activity-events"),
    # Cross-org outputs feed (admin-style, not exposed to CLI today)
    ("GET", "/api/v1/envoy/outputs"),
    # User-facing org CRUD: covered through admin/orgs (super-admin) for CLI users
    ("GET", "/api/v1/organizations/{id}"),
    ("PATCH", "/api/v1/organizations/{id}"),
    ("POST", "/api/v1/organizations"),
    ("GET", "/api/v1/organizations/{id}/subscription"),
    # Stripe webhook (signature-verified) + billing checkout/portal + self-serve
    # onboarding completion: browser-redirect and frontend-only flows.
    ("POST", "/api/v1/webhooks/stripe"),
    ("POST", "/api/v1/billing/checkout-session"),
    ("POST", "/api/v1/billing/checkout-session/verify"),
    ("POST", "/api/v1/billing/portal-session"),
    ("POST", "/api/v1/profiles/me/complete-onboarding"),
}

PARAM_RE = re.compile(r"\{[^}]+\}")
API_REQ_RE = re.compile(
    r"_api_request\(\s*[\"'](?P<method>get|post|put|patch|delete)[\"']\s*,\s*"
    r"(?P<path>f?[\"'][^\"']+[\"']|[A-Z_]+)"
)
# Raw client.request("DELETE", path, ...) — used when the body isn't supported by client.delete()
RAW_REQ_RE = re.compile(
    r"client\.request\(\s*[\"\'](?P<method>GET|POST|PUT|PATCH|DELETE)[\"\']\s*,\s*"
    r"(?P<path>f?[\"\'][^\"\']+[\"\']|[A-Z_]+)"
)
# Direct client.<method>(path, ...) — e.g. client.post for upload endpoints with files=
DIRECT_REQ_RE = re.compile(
    r"client\.(?P<method>get|post|put|patch|delete)\(\s*"
    r"(?P<path>f?[\"\'][^\"\']+[\"\']|[A-Z_]+)"
)


def _normalize(path: str) -> str:
    return PARAM_RE.sub("{id}", path).rstrip("/") or "/"


def _resolve_cli_path(raw: str) -> str | None:
    s = raw.strip()
    if s.startswith("f"):
        s = s[1:]
    if s and s[0] in "\"'":
        s = s[1:-1]
    if s in PATH_CONSTANTS:
        return PATH_CONSTANTS[s]
    if not s:
        return None
    for k in sorted(PATH_CONSTANTS, key=len, reverse=True):
        s = s.replace("{" + k + "}", PATH_CONSTANTS[k])
        s = s.replace(k, PATH_CONSTANTS[k])
    return s if s.startswith("/") else None


def collect_cli_calls(root: Path) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    for py in (root / "src" / "ac_cli" / "commands").rglob("*.py"):
        text = py.read_text()
        for regex in (API_REQ_RE, RAW_REQ_RE, DIRECT_REQ_RE):
            for m in regex.finditer(text):
                method = m.group("method").upper()
                resolved = _resolve_cli_path(m.group("path"))
                if resolved is None:
                    continue
                out.add((method, _normalize(resolved)))
    return out


def fetch_openapi(api_url: str) -> dict | None:
    try:
        with urllib.request.urlopen(f"{api_url.rstrip('/')}/openapi.json", timeout=5) as r:
            return json.loads(r.read())
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        return None


def collect_api_endpoints(spec: dict) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    for raw_path, ops in spec.get("paths", {}).items():
        path = _normalize(raw_path)
        for method in ops:
            if method.lower() in {"get", "post", "put", "patch", "delete"}:
                out.add((method.upper(), path))
    return out


#: OUT_OF_SCOPE paths the OpenAPI spec never declares, so staleness cannot be
#: judged for them.
#:
#: It is empty. It holds a path the API serves outside FastAPI, such as a raw
#: ASGI mount, which appears in no spec. An entry here is exempt from the
#: STALE-SCOPE check and from nothing else.
#:
#: ⚠️ Keep this set small. Every entry is a path no check can watch, so a
#: rename of one is invisible to this tool for ever.
NOT_IN_SPEC: set[str] = set()


def stale_out_of_scope(
    api: set[tuple[str, str]],
) -> set[tuple[str, str]]:
    """Finds OUT_OF_SCOPE entries the live API does not serve.

    An entry is the only thing that keeps a deliberately CLI-omitted endpoint
    out of the API-ONLY list. A typo in one, or an endpoint that was renamed
    or deleted, therefore hides silently: the real path reappears as API-ONLY,
    which is not fatal, and the dead entry keeps suppressing nothing.

    ⚠️ **It only judges an entry whose neighbourhood the API serves.** This
    audit runs against whatever API is up, and a branch API serves routes
    staging does not. Reporting every entry of an absent prefix would fail the
    gate for naming the wrong host, which is a different problem.

    The neighbourhood is the entry's parent path, and not a fixed depth. A
    fixed depth is coarser than the granularity at which staleness happens: a
    route that moves from `/api/v1/webhook` to `/api/v1/nylas/webhook` keeps
    its first three segments, so a three segment test would exempt exactly the
    case this check exists to catch.

    Args:
        api: Every (method, path) the live spec declares, normalized.

    An entry in `NOT_IN_SPEC` is skipped: the spec never declares it, so its
    absence carries no information.

    Returns:
        The entries that name nothing, in a neighbourhood the API serves.
    """
    paths = {path for _, path in api}
    return {
        entry
        for entry in OUT_OF_SCOPE
        if entry not in api
        and entry[1] not in NOT_IN_SPEC
        and _neighbourhood_is_served(entry[1], paths)
    }


def _neighbourhood_is_served(path: str, api_paths: set[str]) -> bool:
    """Answers whether the API serves anything beside one path.

    Args:
        path: The path of an OUT_OF_SCOPE entry.
        api_paths: Every path the live spec declares, normalized.

    Returns:
        True when the spec holds the parent of this path, or anything under
        it. A path with no parent, such as `/health`, is always judged: a
        spec that answered at all serves the root.
    """
    parent = path.rsplit("/", 1)[0]
    if not parent:
        return True
    return any(p == parent or p.startswith(f"{parent}/") for p in api_paths)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--api-url", default=DEFAULT_API_URL, help=f"FastAPI base URL (default: {DEFAULT_API_URL})"
    )
    p.add_argument("--strict", action="store_true", help="exit nonzero if CLI-only paths exist")
    p.add_argument("--show-matches", action="store_true", help="print verbatim-match list too")
    args = p.parse_args()

    spec = fetch_openapi(args.api_url)
    if spec is None:
        print(
            f"ERROR: could not reach {args.api_url}/openapi.json — start the API "
            "or pass --api-url. Static fallback is not implemented because "
            "FastAPI's lazy router mounts can't be resolved by regex alone.",
            file=sys.stderr,
        )
        return 2

    cli = collect_cli_calls(CLI_ROOT)
    api = collect_api_endpoints(spec)

    cli_paths = {p for _, p in cli}
    api_paths = {p for _, p in api}

    cli_only = sorted(c for c in cli if c[1] not in api_paths and c[1] != "/whoami")
    api_only = sorted(a for a in api if a[1] not in cli_paths and a not in OUT_OF_SCOPE)
    method_diff = sorted(
        (m, p) for m, p in cli if (m, p) not in api and p in api_paths and p != "/whoami"
    )
    matches = sorted(c for c in cli if c in api)
    stale_scope = sorted(stale_out_of_scope(api))

    print(f"# ac-cli endpoint audit  (API: {args.api_url})")
    print(f"# CLI calls: {len(cli)}  API endpoints: {len(api)}")
    print(f"# Verbatim matches: {len(matches)}\n")

    print(f"## CLI-ONLY (likely stale) — {len(cli_only)}")
    for m, p in cli_only:
        print(f"  {m:6s} {p}")
    print()

    print(f"## API-ONLY (CLI gap, excluding {len(OUT_OF_SCOPE)} out-of-scope) — {len(api_only)}")
    for m, p in api_only:
        print(f"  {m:6s} {p}")
    print()

    print(f"## STALE-SCOPE (OUT_OF_SCOPE entry the API does not serve) — {len(stale_scope)}")
    for m, p in stale_scope:
        print(f"  {m:6s} {p}")
    print()

    print(f"## METHOD-DIFF (path matches, method differs) — {len(method_diff)}")
    for m, p in method_diff:
        api_methods = sorted(am for am, ap in api if ap == p)
        print(f"  CLI={m} {p} (API has {api_methods})")

    if args.show_matches:
        print(f"\n## MATCHES — {len(matches)}")
        for m, p in matches:
            print(f"  {m:6s} {p}")

    if args.strict and (cli_only or stale_scope):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

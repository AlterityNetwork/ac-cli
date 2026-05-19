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
    "_APPS": "/api/v1/orgs",
    "_CHAT": "/api/v1/chat",
    "_CRM": "/api/v1/crm",
    "_ENVOY": "/api/v1/envoy",
    "_FILES": "/api/v1/files",
    "_HOOKS": "/api/v1/platform/hooks",
    "_IMPERSONATION": "/api/v1/impersonation",
    "_LEGAL": "/api/v1/legal-documents",
    "_MESSAGING": "/api/v1/messaging",
    "_MKT": "/api/v1/marketplace",
    "_NET": "/api/v1/network",
    "_NOTIFICATIONS": "/api/v1/notifications",
    "_NYLAS": "/api/v1/nylas",
    "_ONBOARDING": "/api/v1/admin/onboarding",
    "_ONBOARD": "/api/v1/managed-onboarding",
    "_PROFILES": "/api/v1/profiles",
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
    ("POST", "/api/v1/webhook"),
    ("GET", "/api/v1/webhook"),
    ("GET", "/api/v1/messaging/whatsapp/webhook"),
    ("POST", "/api/v1/messaging/whatsapp/webhook"),
    ("POST", "/api/v1/messaging/slack/events"),
    ("GET", "/api/v1/nylas/oauth/callback"),
    ("GET", "/api/v1/email/unsubscribe"),
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
    # SSE stream — frontend-only consumer (ENG-769)
    ("GET", "/api/v1/notifications/stream"),
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
    # Frontend-only activity logger
    ("POST", "/api/v1/orgs/{id}/activity-events"),
    # Cross-org outputs feed (admin-style, not exposed to CLI today)
    ("GET", "/api/v1/envoy/outputs"),
    # User-facing org CRUD: covered through admin/orgs (super-admin) for CLI users
    ("GET", "/api/v1/profiles"),
    ("GET", "/api/v1/organizations/{id}"),
    ("PATCH", "/api/v1/organizations/{id}"),
    ("POST", "/api/v1/organizations"),
    ("GET", "/api/v1/organizations/{id}/subscription"),
    ("DELETE", "/api/v1/organizations/{id}/subscription/{id}"),
}

PARAM_RE = re.compile(r"\{[^}]+\}")
API_REQ_RE = re.compile(
    r"_api_request\(\s*[\"'](?P<method>get|post|put|patch|delete)[\"']\s*,\s*"
    r"(?P<path>f?[\"'][^\"']+[\"']|[A-Z_]+)"
)
# Raw client.request("DELETE", path, ...) — used when the body isn't supported by client.delete()
RAW_REQ_RE = re.compile(
    r'client\.request\(\s*[\"\'](?P<method>GET|POST|PUT|PATCH|DELETE)[\"\']\s*,\s*'
    r'(?P<path>f?[\"\'][^\"\']+[\"\']|[A-Z_]+)'
)
# Direct client.<method>(path, ...) — e.g. client.post for upload endpoints with files=
DIRECT_REQ_RE = re.compile(
    r'client\.(?P<method>get|post|put|patch|delete)\(\s*'
    r'(?P<path>f?[\"\'][^\"\']+[\"\']|[A-Z_]+)'
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


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--api-url", default=DEFAULT_API_URL,
                   help=f"FastAPI base URL (default: {DEFAULT_API_URL})")
    p.add_argument("--strict", action="store_true",
                   help="exit nonzero if CLI-only paths exist")
    p.add_argument("--show-matches", action="store_true",
                   help="print verbatim-match list too")
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
        (m, p) for m, p in cli
        if (m, p) not in api and p in api_paths and p != "/whoami"
    )
    matches = sorted(c for c in cli if c in api)

    print(f"# ac-cli endpoint audit  (API: {args.api_url})")
    print(f"# CLI calls: {len(cli)}  API endpoints: {len(api)}")
    print(f"# Verbatim matches: {len(matches)}\n")

    print(f"## CLI-ONLY (likely stale) — {len(cli_only)}")
    for m, p in cli_only:
        print(f"  {m:6s} {p}")
    print()

    print(
        f"## API-ONLY (CLI gap, excluding {len(OUT_OF_SCOPE)} out-of-scope)"
        f" — {len(api_only)}"
    )
    for m, p in api_only:
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

    if args.strict and cli_only:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
